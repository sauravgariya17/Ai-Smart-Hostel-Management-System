"""
app/models/password_reset.py
-----------------------------
Stores single-use, time-limited tokens issued for the "Forgot Password"
flow. Storing tokens (hashed) server-side lets us invalidate a token
immediately after use and enforce expiry independent of JWT settings.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from app.extensions import db


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)

    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="reset_tokens")

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """Store only a SHA-256 hash of the token, never the raw value."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def generate_token(cls, user_id: int, expires_in_minutes: int = 60) -> tuple["PasswordResetToken", str]:
        """
        Create a new reset token record and return both the ORM object
        and the raw (unhashed) token string to be emailed to the user.
        """
        raw_token = secrets.token_urlsafe(48)
        token_record = cls(
            user_id=user_id,
            token_hash=cls._hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
        )
        return token_record, raw_token

    @classmethod
    def find_valid_token(cls, raw_token: str) -> "PasswordResetToken | None":
        """Look up a non-expired, unused token record by its raw value."""
        token_hash = cls._hash_token(raw_token)
        record = cls.query.filter_by(token_hash=token_hash, is_used=False).first()
        if record and record.expires_at >= datetime.utcnow():
            return record
        return None

    def mark_used(self) -> None:
        self.is_used = True

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} user_id={self.user_id} used={self.is_used}>"
