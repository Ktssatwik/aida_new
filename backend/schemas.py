from typing import Any

from pydantic import BaseModel, Field


class SQLExecuteRequest(BaseModel):
    dataset_id: str = Field(..., min_length=8, max_length=64)
    sql: str = Field(..., min_length=1, max_length=10000)


class NLToSQLRequest(BaseModel):
    dataset_id: str = Field(..., min_length=8, max_length=64)
    question: str = Field(..., min_length=2, max_length=500)


class NLToSQLResponse(BaseModel):
    dataset_id: str
    table_name: str
    question: str
    generated_sql: str


class NLToSQLExecuteResponse(BaseModel):
    dataset_id: str
    table_name: str
    question: str
    generated_sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
