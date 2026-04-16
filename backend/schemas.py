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


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=72)


class VerifyOTPRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    otp: str = Field(..., min_length=4, max_length=4)


class ResendOTPRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


class MessageResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=72)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=5000)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=5000)


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    is_verified: bool
