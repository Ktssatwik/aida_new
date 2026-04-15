from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from database import Base


class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String(64), unique=True, index=True, nullable=False)
    original_file_name = Column(String(255), nullable=False)
    table_name = Column(String(255), unique=True, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    column_schema_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(String(64), unique=True, index=True, nullable=False)
    dataset_id = Column(String(64), ForeignKey("dataset_registry.dataset_id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    is_safe_sql = Column(Boolean, nullable=False, default=False)
    execution_status = Column(String(32), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
