import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import engine, get_db
from models import DatasetRegistry, User
from services.auth_dependency import get_current_user
from services.sql_validator import validate_sql_read_only

from services.llm_service import generate_sql_from_prompt
from services.prompt_service import build_nl_to_sql_prompt
from services.value_hints_service import extract_value_hints
from schemas import SQLExecuteRequest, NLToSQLRequest, NLToSQLResponse, NLToSQLExecuteResponse
from services.query_log_service import log_query_event


router = APIRouter(tags=["query"])
logger = logging.getLogger("aida_api.query")


def _get_dataset_record(db: Session, dataset_id: str, current_user: User) -> DatasetRegistry:
    """Load dataset metadata record by dataset_id."""
    try:
        record = (
            db.query(DatasetRegistry)
            .filter(DatasetRegistry.dataset_id == dataset_id)
            .first()
        )
    except SQLAlchemyError:
        logger.exception("Failed to fetch dataset metadata for dataset_id=%s", dataset_id)
        raise HTTPException(status_code=500, detail="Database connection error.")

    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to access this dataset.")
    return record


@router.post("/query/sql/execute")
def execute_sql(
    payload: SQLExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate and execute a safe SQL query for the selected dataset."""
    record = _get_dataset_record(db, payload.dataset_id, current_user)

    validated_sql = validate_sql_read_only(payload.sql)

    if record.table_name.lower() not in validated_sql.lower():
        raise HTTPException(
            status_code=400,
            detail=f"SQL must use selected dataset table: {record.table_name}",
        )

    try:
        with engine.connect() as conn:
            result = conn.execute(text(validated_sql))
            rows = result.fetchall()
            columns = list(result.keys())
    except SQLAlchemyError:
        logger.exception("SQL execution failed for dataset_id=%s", payload.dataset_id)
        raise HTTPException(status_code=500, detail="Database execution error.")

    return {
        "dataset_id": record.dataset_id,
        "table_name": record.table_name,
        "executed_sql": validated_sql,
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
    }



@router.post("/query/nl-to-sql", response_model=NLToSQLResponse)
def nl_to_sql(
    payload: NLToSQLRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert natural language question to safe SQL for selected dataset."""
    record = _get_dataset_record(db, payload.dataset_id, current_user)

    try:
        value_hints = extract_value_hints(
            table_name=record.table_name,
            schema_json=record.column_schema_json,
        )
        prompt = build_nl_to_sql_prompt(
            question=payload.question,
            table_name=record.table_name,
            schema_json=record.column_schema_json,
            value_hints=value_hints,
        )

        generated_sql = generate_sql_from_prompt(prompt)
        validated_sql = validate_sql_read_only(generated_sql)

        if record.table_name.lower() not in validated_sql.lower():
            log_query_event(
                db=db,
                dataset_id=record.dataset_id,
                question_text=payload.question,
                generated_sql=generated_sql,
                is_safe_sql=False,
                execution_status="blocked",
                error_message="Generated SQL does not reference selected dataset table.",
            )
            raise HTTPException(
                status_code=400,
                detail=f"Generated SQL must use selected dataset table: {record.table_name}",
            )

        log_query_event(
            db=db,
            dataset_id=record.dataset_id,
            question_text=payload.question,
            generated_sql=validated_sql,
            is_safe_sql=True,
            execution_status="generated",
            error_message=None,
        )

        return NLToSQLResponse(
            dataset_id=record.dataset_id,
            table_name=record.table_name,
            question=payload.question,
            generated_sql=validated_sql,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("NL-to-SQL generation failed for dataset_id=%s", payload.dataset_id)
        log_query_event(
            db=db,
            dataset_id=record.dataset_id,
            question_text=payload.question,
            generated_sql=None,
            is_safe_sql=False,
            execution_status="error",
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail="Failed to generate SQL from question.")



@router.post("/query/nl-to-tables/execute", response_model=NLToSQLExecuteResponse)
def nl_to_sql_execute(
    payload: NLToSQLRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate safe SQL from NL question and execute it."""
    record = _get_dataset_record(db, payload.dataset_id, current_user)

    try:
        value_hints = extract_value_hints(
            table_name=record.table_name,
            schema_json=record.column_schema_json,
        )
        prompt = build_nl_to_sql_prompt(
            question=payload.question,
            table_name=record.table_name,
            schema_json=record.column_schema_json,
            value_hints=value_hints,
        )
        generated_sql = generate_sql_from_prompt(prompt)
        validated_sql = validate_sql_read_only(generated_sql)

        if record.table_name.lower() not in validated_sql.lower():
            log_query_event(
                db=db,
                dataset_id=record.dataset_id,
                question_text=payload.question,
                generated_sql=generated_sql,
                is_safe_sql=False,
                execution_status="blocked",
                error_message="Generated SQL does not reference selected dataset table.",
            )
            raise HTTPException(
                status_code=400,
                detail=f"Generated SQL must use selected dataset table: {record.table_name}",
            )

        with engine.connect() as conn:
            result = conn.execute(text(validated_sql))
            rows = result.fetchall()
            columns = list(result.keys())

        log_query_event(
            db=db,
            dataset_id=record.dataset_id,
            question_text=payload.question,
            generated_sql=validated_sql,
            is_safe_sql=True,
            execution_status="executed",
            error_message=None,
        )

        return NLToSQLExecuteResponse(
            dataset_id=record.dataset_id,
            table_name=record.table_name,
            question=payload.question,
            generated_sql=validated_sql,
            columns=columns,
            rows=[list(r) for r in rows],
            row_count=len(rows),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("NL-to-table execution failed for dataset_id=%s", payload.dataset_id)
        log_query_event(
            db=db,
            dataset_id=record.dataset_id,
            question_text=payload.question,
            generated_sql=None,
            is_safe_sql=False,
            execution_status="error",
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail="Failed to generate/execute SQL.")
