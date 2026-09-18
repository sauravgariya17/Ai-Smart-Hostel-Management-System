"""
app/reports/__init__.py
--------------------------
Blueprint for Reports: aggregate, read-only analytics endpoints
consumed by the reports page and dashboard charts.
"""

from flask import Blueprint

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

from app.reports import routes  # noqa: E402,F401
