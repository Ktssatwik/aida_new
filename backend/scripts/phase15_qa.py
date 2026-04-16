import csv
import io
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

# Ensure backend root is importable when script is run directly.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient

from config import settings
from database import SessionLocal, engine
from main import app
from models import DatasetRegistry, OTPVerification, RefreshToken, User
from services.token_service import create_access_token
from sqlalchemy import text


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def cleanup_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return

        dataset_rows = db.query(DatasetRegistry).filter(DatasetRegistry.user_id == user.id).all()
        table_names = [row.table_name for row in dataset_rows]

        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete(synchronize_session=False)
        db.query(OTPVerification).filter(OTPVerification.user_id == user.id).delete(synchronize_session=False)
        db.query(DatasetRegistry).filter(DatasetRegistry.user_id == user.id).delete(synchronize_session=False)
        db.delete(user)
        db.commit()

        with engine.begin() as conn:
            for table_name in table_names:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
                except Exception:
                    pass
    finally:
        db.close()


def get_latest_otp_row(user_id: int) -> OTPVerification | None:
    db = SessionLocal()
    try:
        return (
            db.query(OTPVerification)
            .filter(OTPVerification.user_id == user_id)
            .order_by(OTPVerification.created_at.desc())
            .first()
        )
    finally:
        db.close()


def get_user(email: str) -> User | None:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()


def set_otp_expired(user_id: int) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(OTPVerification)
            .filter(OTPVerification.user_id == user_id)
            .order_by(OTPVerification.created_at.desc())
            .first()
        )
        if row:
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
    finally:
        db.close()


def set_latest_otp_created_at(user_id: int, dt: datetime) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(OTPVerification)
            .filter(OTPVerification.user_id == user_id)
            .order_by(OTPVerification.created_at.desc())
            .first()
        )
        if row:
            row.created_at = dt
            db.commit()
    finally:
        db.close()


def set_user_verified(email: str, verified: bool) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_verified = verified
            db.commit()
    finally:
        db.close()


def make_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        rows = [{"col1": 1}]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def register_and_verify(client: TestClient, email: str, password: str, otp: str = "1234") -> tuple[int, int]:
    with patch("routes.auth.generate_otp", return_value=otp), patch("routes.auth.send_otp_email", return_value=None):
        r1 = client.post("/auth/register", json={"email": email, "password": password})
        r2 = client.post("/auth/verify-otp", json={"email": email, "otp": otp})
    return r1.status_code, r2.status_code


def main() -> None:
    client = TestClient(app)
    results: list[CheckResult] = []

    email_a = "qa_phase15_a@example.com"
    email_b = "qa_phase15_b@example.com"
    password = "Test@1234"

    cleanup_user(email_a)
    cleanup_user(email_b)

    try:
        # 1) OTP edge cases
        with patch("routes.auth.generate_otp", return_value="1234"), patch(
            "routes.auth.send_otp_email", return_value=None
        ):
            r = client.post("/auth/register", json={"email": email_a, "password": password})
        results.append(CheckResult("otp_register", r.status_code == 200, f"status={r.status_code}"))

        # wrong otp
        r_wrong = client.post("/auth/verify-otp", json={"email": email_a, "otp": "9999"})
        results.append(CheckResult("otp_wrong_value", r_wrong.status_code == 400, f"status={r_wrong.status_code}"))

        # throttling
        with patch("routes.auth.send_otp_email", return_value=None):
            r_throttle = client.post("/auth/resend-otp", json={"email": email_a})
        results.append(
            CheckResult("otp_resend_throttle", r_throttle.status_code == 429, f"status={r_throttle.status_code}")
        )

        # expiry
        user_a = get_user(email_a)
        if user_a:
            set_otp_expired(user_a.id)
        r_expired = client.post("/auth/verify-otp", json={"email": email_a, "otp": "1234"})
        results.append(CheckResult("otp_expired", r_expired.status_code == 400, f"status={r_expired.status_code}"))

        # regenerate OTP then verify success
        if user_a:
            set_latest_otp_created_at(
                user_a.id,
                datetime.now(timezone.utc) - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS + 1),
            )
        with patch("routes.auth.generate_otp", return_value="2222"), patch(
            "routes.auth.send_otp_email", return_value=None
        ):
            _ = client.post("/auth/resend-otp", json={"email": email_a})
        r_verify_ok = client.post("/auth/verify-otp", json={"email": email_a, "otp": "2222"})
        results.append(
            CheckResult("otp_verify_success", r_verify_ok.status_code == 200, f"status={r_verify_ok.status_code}")
        )

        # reused otp -> force user back to unverified to test used-otp rejection path
        set_user_verified(email_a, False)
        r_reuse = client.post("/auth/verify-otp", json={"email": email_a, "otp": "2222"})
        results.append(CheckResult("otp_reused", r_reuse.status_code == 400, f"status={r_reuse.status_code}"))
        set_user_verified(email_a, True)

        # 2) Token lifecycle
        r_login = client.post("/auth/login", json={"email": email_a, "password": password})
        login_body = r_login.json()
        access_a = login_body.get("access_token", "")
        refresh_a = login_body.get("refresh_token", "")
        results.append(CheckResult("token_login", r_login.status_code == 200, f"status={r_login.status_code}"))

        # access token expiry check with forced expired token
        old_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = -1
        expired_access = create_access_token(str(get_user(email_a).id))
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = old_minutes
        r_expired_access = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_access}"})
        results.append(
            CheckResult("token_access_expiry", r_expired_access.status_code == 401, f"status={r_expired_access.status_code}")
        )

        # refresh rotation
        r_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_a})
        refresh_body = r_refresh.json()
        refresh_rotated = refresh_body.get("refresh_token", "")
        results.append(CheckResult("token_refresh_rotate", r_refresh.status_code == 200, f"status={r_refresh.status_code}"))

        # old refresh should now fail
        r_old_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_a})
        results.append(
            CheckResult("token_old_refresh_revoked", r_old_refresh.status_code == 401, f"status={r_old_refresh.status_code}")
        )

        # logout revocation
        r_logout = client.post("/auth/logout", json={"refresh_token": refresh_rotated})
        results.append(CheckResult("token_logout", r_logout.status_code == 200, f"status={r_logout.status_code}"))

        r_after_logout = client.post("/auth/refresh", json={"refresh_token": refresh_rotated})
        results.append(
            CheckResult("token_after_logout_revoked", r_after_logout.status_code == 401, f"status={r_after_logout.status_code}")
        )

        # 3) Isolation with 2 users + uploads
        reg_b, ver_b = register_and_verify(client, email_b, password, otp="4444")
        results.append(CheckResult("user_b_register", reg_b == 200, f"status={reg_b}"))
        results.append(CheckResult("user_b_verify", ver_b == 200, f"status={ver_b}"))

        login_b = client.post("/auth/login", json={"email": email_b, "password": password})
        access_b = login_b.json().get("access_token", "")
        refresh_b = login_b.json().get("refresh_token", "")
        results.append(CheckResult("user_b_login", login_b.status_code == 200, f"status={login_b.status_code}"))

        csv_a = make_csv_bytes([{"name": "alice", "value": 10}, {"name": "bob", "value": 12}])
        csv_b = make_csv_bytes([{"name": "x", "value": 3}, {"name": "y", "value": 7}])

        up_a = client.post(
            "/datasets/upload",
            headers={"Authorization": f"Bearer {access_a}"},
            files={"file": ("a.csv", csv_a, "text/csv")},
        )
        up_b = client.post(
            "/datasets/upload",
            headers={"Authorization": f"Bearer {access_b}"},
            files={"file": ("b.csv", csv_b, "text/csv")},
        )
        results.append(CheckResult("upload_user_a", up_a.status_code == 200, f"status={up_a.status_code}"))
        results.append(CheckResult("upload_user_b", up_b.status_code == 200, f"status={up_b.status_code}"))

        dataset_a = up_a.json().get("dataset_id")
        table_a = up_a.json().get("table_name")
        dataset_b = up_b.json().get("dataset_id")
        table_b = up_b.json().get("table_name")

        list_a = client.get("/datasets", headers={"Authorization": f"Bearer {access_a}"})
        list_b = client.get("/datasets", headers={"Authorization": f"Bearer {access_b}"})
        a_ids = {row.get("dataset_id") for row in (list_a.json() if list_a.status_code == 200 else [])}
        b_ids = {row.get("dataset_id") for row in (list_b.json() if list_b.status_code == 200 else [])}

        results.append(CheckResult("isolation_list_a_own", dataset_a in a_ids, f"a_has_own={dataset_a in a_ids}"))
        results.append(CheckResult("isolation_list_a_not_b", dataset_b not in a_ids, f"a_has_b={dataset_b in a_ids}"))
        results.append(CheckResult("isolation_list_b_own", dataset_b in b_ids, f"b_has_own={dataset_b in b_ids}"))
        results.append(CheckResult("isolation_list_b_not_a", dataset_a not in b_ids, f"b_has_a={dataset_a in b_ids}"))

        cross_schema = client.get(
            f"/datasets/{dataset_b}/schema",
            headers={"Authorization": f"Bearer {access_a}"},
        )
        results.append(CheckResult("isolation_schema_forbidden", cross_schema.status_code == 403, f"status={cross_schema.status_code}"))

        cross_query = client.post(
            "/query/sql/execute",
            headers={"Authorization": f"Bearer {access_a}"},
            json={"dataset_id": dataset_b, "sql": f"SELECT * FROM {table_b} LIMIT 1"},
        )
        results.append(CheckResult("isolation_query_forbidden", cross_query.status_code == 403, f"status={cross_query.status_code}"))

        own_query = client.post(
            "/query/sql/execute",
            headers={"Authorization": f"Bearer {access_a}"},
            json={"dataset_id": dataset_a, "sql": f"SELECT * FROM {table_a} LIMIT 1"},
        )
        results.append(CheckResult("isolation_own_query_ok", own_query.status_code == 200, f"status={own_query.status_code}"))

        # cleanup active session B token
        if refresh_b:
            client.post("/auth/logout", json={"refresh_token": refresh_b})

    finally:
        cleanup_user(email_a)
        cleanup_user(email_b)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"Phase15 QA: {passed}/{total} checks passed")
    for item in results:
        status_txt = "PASS" if item.passed else "FAIL"
        print(f"- [{status_txt}] {item.name}: {item.detail}")

    failed = [r for r in results if not r.passed]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
