from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import get_settings


def send_otp_email(to_email: str, full_name: str, otp: str, purpose: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        print(f"[SmartVote DEV OTP] {purpose} for {to_email}: {otp}")
        return False

    subject = "Your SmartVote OTP"
    if purpose == "FORGOT_PASSWORD":
        subject = "Reset your SmartVote password"
    elif purpose == "EMAIL_VERIFICATION":
        subject = "Verify your SmartVote email"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_email
    message.set_content(
        f"""Hi {full_name},

Your SmartVote OTP is {otp}.

Purpose: {purpose.replace('_', ' ').title()}
This code expires in {settings.otp_expiry_minutes} minutes.

SmartVote Security Team
"""
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
    return True
