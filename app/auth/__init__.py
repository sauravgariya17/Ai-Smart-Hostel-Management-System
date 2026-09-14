"""
app/auth/__init__.py
----------------------
Defines the "auth" blueprint. Routes are attached in app/auth/routes.py
(imported at the bottom to avoid circular imports).
"""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

from app.auth import routes  # noqa: E402,F401
