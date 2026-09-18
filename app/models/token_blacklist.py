"""
app/models/token_blacklist.py
-------------------------------
Tracks revoked JWTs (by their unique "jti" claim) so that logged-out or
force-revoked tokens are rejected even though they haven't naturally
expired yet. Checked on every protected request via the
`jwt.token_in_blocklist_loader` callback registered in app/__init__.py.
"""

from datetime import datetime

from app.extensions import db


class TokenBlacklist(db.Model):
    __tablename__ = "token_blacklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)  # "access" or "refresh"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TokenBlacklist jti={self.jti} type={self.token_type}>"
