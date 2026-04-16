import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import OTPVerification, RefreshToken, User
from schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendOTPRequest,
    TokenPairResponse,
    VerifyOTPRequest,
)
from services.auth_dependency import get_current_user
from services.email_service import send_otp_email
from services.otp_service import generate_otp, hash_otp, otp_expiry_time, verify_otp
from services.password_service import hash_password, verify_password
from services.token_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    token_expiry_from_payload,
    verify_token_type,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("aida_api.auth")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _log_auth_event(
    event: str,
    status_value: str,
    email: str | None = None,
    user_id: int | None = None,
    reason: str | None = None,
) -> None:
    logger.info(
        "AUTH_EVENT event=%s status=%s email=%s user_id=%s reason=%s",
        event,
        status_value,
        email or "-",
        user_id if user_id is not None else "-",
        reason or "-",
    )


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_REGEX.match(normalized):
        raise HTTPException(status_code=400, detail="Invalid email format.")
    return normalized


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _latest_otp_record(db: Session, user_id: int) -> OTPVerification | None:
    return (
        db.query(OTPVerification)
        .filter(OTPVerification.user_id == user_id)
        .order_by(OTPVerification.created_at.desc())
        .first()
    )


def _latest_refresh_record(db: Session, user_id: int, token_hash: str) -> Optional[RefreshToken]:
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.token_hash == token_hash)
        .order_by(RefreshToken.created_at.desc())
        .first()
    )


def _store_refresh_token(db: Session, user_id: int, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    verify_token_type(payload, "refresh")
    expires_at = token_expiry_from_payload(payload)

    refresh_row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=expires_at,
        revoked_at=None,
    )
    db.add(refresh_row)
    db.commit()


def _create_and_send_otp(db: Session, user_id: int, email: str) -> None:
    otp = generate_otp()
    otp_record = OTPVerification(
        user_id=user_id,
        otp_hash=hash_otp(otp),
        expires_at=otp_expiry_time(),
        attempts_count=0,
        is_used=False,
        created_at=datetime.utcnow(),
    )
    db.add(otp_record)
    db.commit()
    send_otp_email(email, otp)


@router.post("/register", response_model=MessageResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register user and send email OTP for verification."""
    email = _normalize_email(payload.email)

    try:
        user = db.query(User).filter(User.email == email).first()
    except SQLAlchemyError:
        logger.exception("Failed to query user during register.")
        raise HTTPException(status_code=500, detail="Database connection error.")

    if user and user.is_verified:
        _log_auth_event("register", "failed", email=email, user_id=user.id, reason="email_exists")
        raise HTTPException(status_code=409, detail="Email is already registered.")

    if not user:
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            is_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)

    try:
        _create_and_send_otp(db, user.id, email)
    except HTTPException:
        _log_auth_event("register", "failed", email=email, user_id=user.id, reason="otp_send_failed")
        raise
    except Exception:
        logger.exception("Register OTP send failed for email=%s", email)
        _log_auth_event("register", "failed", email=email, user_id=user.id, reason="otp_send_exception")
        raise HTTPException(status_code=500, detail="Failed to generate/send OTP.")

    _log_auth_event("register", "success", email=email, user_id=user.id)
    return MessageResponse(message="Registration successful. OTP sent to email.")


@router.post("/verify-otp", response_model=MessageResponse)
def verify_user_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify OTP, enforce attempts/expiry, and mark user as verified."""
    email = _normalize_email(payload.email)

    try:
        user = db.query(User).filter(User.email == email).first()
    except SQLAlchemyError:
        logger.exception("Failed to query user during OTP verify.")
        raise HTTPException(status_code=500, detail="Database connection error.")

    if not user:
        _log_auth_event("verify_otp", "failed", email=email, reason="user_not_found")
        raise HTTPException(status_code=404, detail="User not found.")
    if user.is_verified:
        _log_auth_event("verify_otp", "skipped", email=email, user_id=user.id, reason="already_verified")
        return MessageResponse(message="User already verified.")

    otp_record = _latest_otp_record(db, user.id)
    if not otp_record or otp_record.is_used:
        _log_auth_event("verify_otp", "failed", email=email, user_id=user.id, reason="no_active_otp")
        raise HTTPException(status_code=400, detail="No active OTP found. Please request a new OTP.")

    now_utc_naive = datetime.utcnow()
    expires_utc_naive = _to_utc_naive(otp_record.expires_at)
    if expires_utc_naive < now_utc_naive:
        _log_auth_event("verify_otp", "failed", email=email, user_id=user.id, reason="otp_expired")
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new OTP.")

    if otp_record.attempts_count >= settings.OTP_MAX_ATTEMPTS:
        _log_auth_event("verify_otp", "failed", email=email, user_id=user.id, reason="max_attempts")
        raise HTTPException(status_code=429, detail="Maximum OTP attempts reached. Please resend OTP.")

    if not verify_otp(payload.otp, otp_record.otp_hash):
        otp_record.attempts_count += 1
        db.commit()
        _log_auth_event("verify_otp", "failed", email=email, user_id=user.id, reason="invalid_otp")
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    otp_record.is_used = True
    user.is_verified = True
    db.commit()

    _log_auth_event("verify_otp", "success", email=email, user_id=user.id)
    return MessageResponse(message="OTP verified successfully. Account is now active.")


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(payload: ResendOTPRequest, db: Session = Depends(get_db)):
    """Resend OTP with cooldown and max-attempt safety."""
    email = _normalize_email(payload.email)

    try:
        user = db.query(User).filter(User.email == email).first()
    except SQLAlchemyError:
        logger.exception("Failed to query user during resend OTP.")
        raise HTTPException(status_code=500, detail="Database connection error.")

    if not user:
        _log_auth_event("resend_otp", "failed", email=email, reason="user_not_found")
        raise HTTPException(status_code=404, detail="User not found.")
    if user.is_verified:
        _log_auth_event("resend_otp", "failed", email=email, user_id=user.id, reason="already_verified")
        raise HTTPException(status_code=400, detail="User is already verified.")

    latest = _latest_otp_record(db, user.id)
    if latest:
        created_utc_naive = _to_utc_naive(latest.created_at)
        elapsed_seconds = (datetime.utcnow() - created_utc_naive).total_seconds()
        if elapsed_seconds < settings.OTP_RESEND_COOLDOWN_SECONDS:
            retry_after = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed_seconds)
            _log_auth_event("resend_otp", "failed", email=email, user_id=user.id, reason="cooldown")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {max(retry_after, 1)} seconds before resending OTP.",
            )

    try:
        db.query(OTPVerification).filter(
            OTPVerification.user_id == user.id,
            OTPVerification.is_used.is_(False),
        ).update({"is_used": True}, synchronize_session=False)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to invalidate old OTPs for user_id=%s", user.id)
        _log_auth_event("resend_otp", "failed", email=email, user_id=user.id, reason="db_error")
        raise HTTPException(status_code=500, detail="Failed to resend OTP.")

    try:
        _create_and_send_otp(db, user.id, email)
    except HTTPException:
        _log_auth_event("resend_otp", "failed", email=email, user_id=user.id, reason="otp_send_failed")
        raise
    except Exception:
        logger.exception("Resend OTP failed for email=%s", email)
        _log_auth_event("resend_otp", "failed", email=email, user_id=user.id, reason="otp_send_exception")
        raise HTTPException(status_code=500, detail="Failed to resend OTP.")

    _log_auth_event("resend_otp", "success", email=email, user_id=user.id)
    return MessageResponse(message="New OTP sent to email.")


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login verified user and issue access + refresh tokens."""
    email = _normalize_email(payload.email)

    try:
        user = db.query(User).filter(User.email == email).first()
    except SQLAlchemyError:
        logger.exception("Failed to query user during login.")
        raise HTTPException(status_code=500, detail="Database connection error.")

    if not user:
        _log_auth_event("login", "failed", email=email, reason="user_not_found")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not verify_password(payload.password, user.password_hash):
        _log_auth_event("login", "failed", email=email, user_id=user.id, reason="invalid_password")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_verified:
        _log_auth_event("login", "failed", email=email, user_id=user.id, reason="not_verified")
        raise HTTPException(status_code=403, detail="User is not verified. Please verify OTP.")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    try:
        _store_refresh_token(db, user.id, refresh_token)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to store refresh token for user_id=%s", user.id)
        _log_auth_event("login", "failed", email=email, user_id=user.id, reason="session_store_failed")
        raise HTTPException(status_code=500, detail="Failed to create login session.")

    _log_auth_event("login", "success", email=email, user_id=user.id)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Validate refresh token, rotate it, and issue new token pair."""
    decoded = decode_token(payload.refresh_token)
    verify_token_type(decoded, "refresh")

    subject = decoded.get("sub")
    if subject is None:
        _log_auth_event("refresh", "failed", reason="missing_subject")
        raise HTTPException(status_code=401, detail="Invalid refresh token payload.")

    try:
        user_id = int(subject)
    except ValueError:
        _log_auth_event("refresh", "failed", reason="invalid_subject")
        raise HTTPException(status_code=401, detail="Invalid refresh token subject.")

    token_hash = hash_refresh_token(payload.refresh_token)
    record = _latest_refresh_record(db, user_id, token_hash)
    if not record:
        _log_auth_event("refresh", "failed", user_id=user_id, reason="token_not_found")
        raise HTTPException(status_code=401, detail="Refresh token not found.")
    if record.revoked_at is not None:
        _log_auth_event("refresh", "failed", user_id=user_id, reason="token_revoked")
        raise HTTPException(status_code=401, detail="Refresh token has been revoked.")

    expires_at = _to_utc_naive(record.expires_at)
    if expires_at < datetime.utcnow():
        record.revoked_at = datetime.utcnow()
        db.commit()
        _log_auth_event("refresh", "failed", user_id=user_id, reason="token_expired")
        raise HTTPException(status_code=401, detail="Refresh token expired.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        _log_auth_event("refresh", "failed", user_id=user_id, reason="user_not_found")
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_verified:
        _log_auth_event("refresh", "failed", user_id=user_id, reason="not_verified")
        raise HTTPException(status_code=403, detail="User is not verified.")

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    try:
        record.revoked_at = datetime.utcnow()
        db.commit()
        _store_refresh_token(db, user.id, new_refresh_token)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to rotate refresh token for user_id=%s", user.id)
        _log_auth_event("refresh", "failed", user_id=user.id, reason="rotation_failed")
        raise HTTPException(status_code=500, detail="Failed to refresh session.")

    _log_auth_event("refresh", "success", email=user.email, user_id=user.id)
    return TokenPairResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, response: Response, db: Session = Depends(get_db)):
    """Revoke refresh token and clear auth cookies."""
    decoded = decode_token(payload.refresh_token)
    verify_token_type(decoded, "refresh")

    subject = decoded.get("sub")
    if subject is None:
        _log_auth_event("logout", "failed", reason="missing_subject")
        raise HTTPException(status_code=401, detail="Invalid refresh token payload.")

    try:
        user_id = int(subject)
    except ValueError:
        _log_auth_event("logout", "failed", reason="invalid_subject")
        raise HTTPException(status_code=401, detail="Invalid refresh token subject.")

    token_hash = hash_refresh_token(payload.refresh_token)
    record = _latest_refresh_record(db, user_id, token_hash)
    if not record:
        _log_auth_event("logout", "failed", user_id=user_id, reason="token_not_found")
        raise HTTPException(status_code=401, detail="Refresh token not found.")

    if record.revoked_at is None:
        record.revoked_at = datetime.utcnow()
        db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    _log_auth_event("logout", "success", user_id=user_id)
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=CurrentUserResponse)
def auth_me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user from access token."""
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        is_verified=current_user.is_verified,
    )
