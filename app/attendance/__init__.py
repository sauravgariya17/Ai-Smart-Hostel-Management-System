"""
app/attendance/__init__.py
------------------------------
Blueprint for Attendance Management (daily marking + history/reporting).
"""

from flask import Blueprint

attendance_bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")

from app.attendance import routes  # noqa: E402,F401
