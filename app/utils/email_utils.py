"""
app/utils/email_utils.py
---------------------------
Wraps Flask-Mail to send transactional emails (currently: password
reset links). If mail credentials are not configured (typical in local
development), the email content is logged to the console instead of
raising an error, so the "Forgot Password" flow remains testable
end-to-end without a real SMTP server.
"""

import logging

from flask import current_app
from flask_mail import Message

from app.extensions import mail

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_link: str, user_name: str = "") -> None:
    subject = "Reset Your Smart Hostel Management System Password"
    greeting = f"Hello {user_name}," if user_name else "Hello,"

    body = (
        f"{greeting}\n\n"
        "We received a request to reset your password for the "
        "AI-Powered Smart Hostel Management System.\n\n"
        f"Click the link below to set a new password. This link expires soon:\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can safely ignore this email.\n\n"
        "Regards,\nSmart Hostel Management System"
    )

    mail_configured = bool(current_app.config.get("MAIL_USERNAME"))

    if not mail_configured:
        # Development fallback: log instead of sending, so the flow is
        # still testable without real SMTP credentials configured.
        logger.warning("MAIL_USERNAME not configured. Logging reset email instead of sending.")
        logger.info("---- PASSWORD RESET EMAIL (DEV MODE) ----")
        logger.info("To: %s", to_email)
        logger.info("Subject: %s", subject)
        logger.info("Body:\n%s", body)
        logger.info("------------------------------------------")
        return

    message = Message(subject=subject, recipients=[to_email], body=body)
    mail.send(message)
