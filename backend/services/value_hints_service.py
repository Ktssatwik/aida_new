import json
import re
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CATEGORICAL_DTYPES = {"object", "string", "str", "category", "bool", "boolean"}


def _is_safe_identifier(name: str) -> bool:
    return bool(_SAFE_IDENTIFIER.match(name))


def extract_value_hints(
    table_name: str,
    schema_json: str | None,
    max_columns: int = 8,
    max_values_per_column: int = 10,
) -> Dict[str, List[str]]:
    """Return low-cardinality distinct values for categorical columns."""
    if not _is_safe_identifier(table_name):
        return {}

    try:
        schema_map: Dict[str, str] = json.loads(schema_json) if schema_json else {}
    except Exception:
        return {}

    candidate_columns: List[str] = []
    for col, dtype in schema_map.items():
        normalized_dtype = str(dtype).lower()
        if any(token in normalized_dtype for token in _CATEGORICAL_DTYPES):
            if _is_safe_identifier(col):
                candidate_columns.append(col)

    if not candidate_columns:
        return {}

    value_hints: Dict[str, List[str]] = {}
    for col in candidate_columns[:max_columns]:
        sql = text(
            f"SELECT DISTINCT `{col}` AS value FROM `{table_name}` "
            f"WHERE `{col}` IS NOT NULL LIMIT :limit"
        )
        try:
            with engine.connect() as conn:
                rows = conn.execute(sql, {"limit": max_values_per_column}).fetchall()
        except SQLAlchemyError:
            continue

        values: List[str] = []
        for row in rows:
            raw = row[0]
            if raw is None:
                continue
            text_value = str(raw).strip()
            if text_value:
                values.append(text_value)

        if values:
            value_hints[col] = values

    return value_hints
