import json
import logging
import re
import uuid
from datetime import datetime

import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import engine, get_db
from models import DatasetRegistry

router = APIRouter(tags=["datasets"])
logger = logging.getLogger("aida_api.datasets")


def _sanitize_column_name(name: str) -> str:
    """Sanitize a CSV column name to a safe MySQL identifier."""
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip().lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean:
        clean = "col"
    if clean[0].isdigit():
        clean = f"col_{clean}"
    return clean[:64]


def _make_unique_columns(columns: list[str]) -> list[str]:
    """Ensure sanitized column names are unique."""
    seen = {}
    unique_cols = []

    for col in columns:
        base = _sanitize_column_name(col)
        if base not in seen:
            seen[base] = 1
            unique_cols.append(base)
        else:
            seen[base] += 1
            unique_cols.append(f"{base}_{seen[base]}")
    return unique_cols


def _generate_table_name(filename: str) -> str:
    """Generate a unique table name for each uploaded CSV."""
    base = filename.rsplit(".", 1)[0].lower()
    base = re.sub(r"[^a-z0-9_]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "dataset"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"ds_{timestamp}_{base[:24]}_{suffix}"


@router.post("/datasets/upload")
def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload CSV, create a new MySQL table, and store metadata."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        df = pd.read_csv(file.file)
    except EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV is empty.")
    except ParserError:
        raise HTTPException(status_code=400, detail="Invalid CSV format.")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV encoding is not supported.")
    except Exception:
        logger.exception("Unexpected CSV read failure for file: %s", file.filename)
        raise HTTPException(status_code=400, detail="Invalid CSV file.")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV is empty.")

    if len(df) > 20000:
        raise HTTPException(
            status_code=400,
            detail="CSV row limit exceeded. Max allowed is 20000 rows.",
        )

    if len(df.columns) == 0:
        raise HTTPException(status_code=400, detail="CSV has no columns.")

    df.columns = _make_unique_columns(list(df.columns))
    table_name = _generate_table_name(file.filename)

    try:
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="fail",
            index=False,
            method="multi",
            chunksize=1000,
        )
    except Exception as exc:
        logger.exception("Failed to create table %s from upload %s", table_name, file.filename)
        raise HTTPException(status_code=500, detail=f"Failed to write CSV to MySQL: {exc}")

    dataset_id = str(uuid.uuid4())
    schema_map = {col: str(dtype) for col, dtype in df.dtypes.items()}

    record = DatasetRegistry(
        dataset_id=dataset_id,
        original_file_name=file.filename,
        table_name=table_name,
        row_count=int(len(df)),
        column_schema_json=json.dumps(schema_map),
        status="active",
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to write dataset registry record for table: %s", table_name)
        raise HTTPException(status_code=500, detail="Failed to store dataset metadata.")

    return {
        "dataset_id": dataset_id,
        "table_name": table_name,
        "row_count": int(len(df)),
        "columns": [{"name": col, "dtype": str(dtype)} for col, dtype in df.dtypes.items()],
    }


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    """Return all uploaded datasets for UI selection."""
    try:
        rows = db.query(DatasetRegistry).order_by(DatasetRegistry.uploaded_at.desc()).all()
    except SQLAlchemyError:
        logger.exception("Failed to fetch dataset list.")
        raise HTTPException(status_code=500, detail="Database connection error.")

    return [
        {
            "dataset_id": row.dataset_id,
            "file_name": row.original_file_name,
            "table_name": row.table_name,
            "row_count": row.row_count,
            "uploaded_at": row.uploaded_at,
            "status": row.status,
        }
        for row in rows
    ]


@router.get("/datasets/{dataset_id}/schema")
def get_dataset_schema(dataset_id: str, db: Session = Depends(get_db)):
    """Return metadata and schema for one dataset."""
    try:
        record = (
            db.query(DatasetRegistry)
            .filter(DatasetRegistry.dataset_id == dataset_id)
            .first()
        )
    except SQLAlchemyError:
        logger.exception("Failed to fetch dataset schema for dataset_id=%s", dataset_id)
        raise HTTPException(status_code=500, detail="Database connection error.")

    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        schema = json.loads(record.column_schema_json) if record.column_schema_json else {}
    except Exception:
        schema = {}

    return {
        "dataset_id": record.dataset_id,
        "file_name": record.original_file_name,
        "table_name": record.table_name,
        "row_count": record.row_count,
        "uploaded_at": record.uploaded_at,
        "schema": [{"name": key, "dtype": value} for key, value in schema.items()],
    }
