import re

from fastapi import HTTPException

FORBIDDEN_SQL_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "replace",
    "rename",
}


def validate_sql_read_only(sql: str) -> str:
    """Allow only safe read-only SQL and enforce a row limit."""
    if not sql or not sql.strip():
        raise HTTPException(status_code=400, detail="SQL is empty.")

    sql_clean = sql.strip()
    sql_lower = sql_clean.lower()

    if sql_clean.endswith(";"):
        sql_clean = sql_clean[:-1].strip()
        sql_lower = sql_clean.lower()

    if ";" in sql_clean:
        raise HTTPException(status_code=400, detail="Multiple statements are not allowed.")

    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        raise HTTPException(status_code=400, detail="Only SELECT/WITH queries are allowed.")

    if "--" in sql_clean or "/*" in sql_clean or "*/" in sql_clean:
        raise HTTPException(status_code=400, detail="SQL comments are not allowed.")

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_lower):
            raise HTTPException(status_code=400, detail=f"Forbidden SQL keyword: {keyword}")

    if " limit " not in f" {sql_lower} ":
        sql_clean = f"{sql_clean}"

    return sql_clean
