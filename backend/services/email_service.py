import logging
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException

from config import settings

logger = logging.getLogger("aida_api.email")


def send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP to user email via SMTP."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise HTTPException(status_code=500, detail="SMTP credentials are not configured.")

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER

    message = EmailMessage()
    message["Subject"] = "Your AIDA Verification OTP"
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(
        (
            f"Your OTP is: {otp}\n\n"
            f"This OTP is valid for {settings.OTP_EXPIRE_MINUTES} minutes.\n"
            "If you did not request this, please ignore this email."
        )
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception:
        logger.exception("Failed to send OTP email to %s", to_email)
        raise HTTPException(status_code=500, detail="Failed to send OTP email.")
