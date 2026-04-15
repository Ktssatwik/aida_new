import uuid
from typing import Optional
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import QueryLog

logger = logging.getLogger("aida_api.query_logs")

def log_query_event(
    db: Session,
    dataset_id: str,
    question_text: str,
    generated_sql: Optional[str],
    is_safe_sql: bool,
    execution_status: str,
    error_message: Optional[str] = None,
) -> None:
    """Insert one query log record into query_logs."""
    row = QueryLog(
        query_id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        question_text=question_text,
        generated_sql=generated_sql,
        is_safe_sql=is_safe_sql,
        execution_status=execution_status,
        error_message=error_message,
    )
    try:
        db.add(row)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to persist query log for dataset_id=%s", dataset_id)
