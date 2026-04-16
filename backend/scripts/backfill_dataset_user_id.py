import argparse

from sqlalchemy.orm import Session

from database import SessionLocal
from models import DatasetRegistry, User


def backfill_orphan_datasets(target_email: str, dry_run: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == target_email.lower().strip()).first()
        if not user:
            print(f"User not found for email: {target_email}")
            return

        orphan_count = db.query(DatasetRegistry).filter(DatasetRegistry.user_id.is_(None)).count()
        print(f"Orphan dataset rows found: {orphan_count}")

        if orphan_count == 0:
            print("Nothing to backfill.")
            return

        if dry_run:
            print("Dry run enabled. No rows were updated.")
            return

        updated = (
            db.query(DatasetRegistry)
            .filter(DatasetRegistry.user_id.is_(None))
            .update({"user_id": user.id}, synchronize_session=False)
        )
        db.commit()
        print(f"Backfill complete. Rows updated: {updated}. Assigned to user_id={user.id}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill dataset_registry.user_id for orphan rows.")
    parser.add_argument("--email", required=True, help="Target user email to assign orphan datasets.")
    parser.add_argument("--dry-run", action="store_true", help="Show orphan count without updating rows.")
    args = parser.parse_args()

    backfill_orphan_datasets(target_email=args.email, dry_run=args.dry_run)
