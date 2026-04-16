import hashlib
import random
from datetime import datetime, timedelta

from config import settings


def generate_otp() -> str:
    """Generate a 4-digit numeric OTP string."""
    return f"{random.randint(0, 9999):04d}"


def hash_otp(otp: str) -> str:
    """Hash OTP with app secret for safer storage."""
    secret = settings.JWT_SECRET_KEY or "default_secret"
    payload = f"{otp}:{secret}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_otp(plain_otp: str, otp_hash: str) -> bool:
    """Verify plain OTP against stored hash."""
    return hash_otp(plain_otp) == otp_hash


def otp_expiry_time() -> datetime:
    """Return OTP expiry timestamp using configured TTL."""
    return datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
