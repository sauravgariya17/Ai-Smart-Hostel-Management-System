"""
app/utils/validators.py
-------------------------
Lightweight, dependency-free request payload validators used across the
auth blueprint. Each validator returns a list of human-readable error
strings; an empty list means the payload is valid.
"""

import re

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# At least 8 chars, one uppercase, one lowercase, one digit, one special char.
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+{};:,<.>?]).{8,}$"
)


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))


def is_strong_password(password: str) -> bool:
    return bool(password) and bool(PASSWORD_REGEX.match(password))


def validate_registration_payload(data: dict, required_fields: list[str]) -> list[str]:
    errors = []

    for field in required_fields:
        if not data.get(field):
            errors.append(f"'{field}' is required.")

    email = data.get("email", "")
    if email and not is_valid_email(email):
        errors.append("A valid email address is required.")

    password = data.get("password", "")
    if password and not is_strong_password(password):
        errors.append(
            "Password must be at least 8 characters and include an uppercase letter, "
            "a lowercase letter, a digit, and a special character."
        )

    return errors


def validate_login_payload(data: dict) -> list[str]:
    errors = []
    if not data.get("email"):
        errors.append("'email' is required.")
    if not data.get("password"):
        errors.append("'password' is required.")
    return errors


PHONE_REGEX = re.compile(r"^[0-9+\-\s]{7,20}$")


def is_valid_phone(phone: str) -> bool:
    return bool(phone) and bool(PHONE_REGEX.match(phone.strip()))


def is_valid_date(value: str) -> bool:
    if not value:
        return False
    from datetime import datetime
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_positive_amount(value) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def validate_required_fields(data: dict, required_fields: list[str]) -> list[str]:
    """Generic required-field checker reused by every module's create/update payloads."""
    errors = []
    for field in required_fields:
        if data.get(field) in (None, "", []):
            errors.append(f"'{field}' is required.")
    return errors


def validate_choice(value, allowed_values: list[str], field_name: str) -> list[str]:
    """Return an error list (0 or 1 items) if `value` isn't one of `allowed_values`."""
    if value is not None and value not in allowed_values:
        return [f"'{field_name}' must be one of: {', '.join(allowed_values)}."]
    return []
