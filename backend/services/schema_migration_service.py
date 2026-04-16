import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from database import engine

logger = logging.getLogger("aida_api.migration")


def ensure_dataset_registry_user_id_column() -> None:
    """Ensure dataset_registry has user_id column/index/FK for ownership isolation."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "dataset_registry" not in table_names:
        return

    columns = {col["name"] for col in inspector.get_columns("dataset_registry")}

    try:
        with engine.begin() as conn:
            if "user_id" not in columns:
                conn.execute(text("ALTER TABLE dataset_registry ADD COLUMN user_id INT NULL"))
                logger.info("Added dataset_registry.user_id column.")
    except SQLAlchemyError:
        logger.exception("Failed to add dataset_registry.user_id column.")
        return

    inspector = inspect(engine)
    index_names = {idx["name"] for idx in inspector.get_indexes("dataset_registry")}
    if "ix_dataset_registry_user_id" not in index_names:
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX ix_dataset_registry_user_id ON dataset_registry (user_id)"))
            logger.info("Created index ix_dataset_registry_user_id.")
        except SQLAlchemyError:
            logger.exception("Failed to create index ix_dataset_registry_user_id.")

    foreign_keys = inspector.get_foreign_keys("dataset_registry")
    fk_names = {fk.get("name") for fk in foreign_keys if fk.get("name")}
    fk_name = "fk_dataset_registry_user_id_users"

    if fk_name not in fk_names:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE dataset_registry "
                        "ADD CONSTRAINT fk_dataset_registry_user_id_users "
                        "FOREIGN KEY (user_id) REFERENCES users(id)"
                    )
                )
            logger.info("Added FK fk_dataset_registry_user_id_users.")
        except SQLAlchemyError:
            logger.exception("Failed to add FK fk_dataset_registry_user_id_users.")


def count_orphan_datasets() -> int:
    """Count dataset rows that are not assigned to any user (for backfill planning)."""
    try:
        with engine.connect() as conn:
            value = conn.execute(
                text("SELECT COUNT(*) AS cnt FROM dataset_registry WHERE user_id IS NULL")
            ).scalar()
        return int(value or 0)
    except SQLAlchemyError:
        logger.exception("Failed to count orphan datasets.")
        return 0
