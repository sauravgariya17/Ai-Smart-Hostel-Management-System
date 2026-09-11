"""
app/fees/__init__.py
-----------------------
Blueprint for Fee Management (fee structures + student invoices) and
Payment History (payments recorded against invoices).
"""

from flask import Blueprint

fees_bp = Blueprint("fees", __name__, url_prefix="/api/fees")

from app.fees import routes  # noqa: E402,F401
