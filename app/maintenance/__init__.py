"""
app/maintenance/__init__.py
-------------------------------
Blueprint for Maintenance Management (repair/work orders raised against
rooms or common hostel infrastructure).
"""

from flask import Blueprint

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")

from app.maintenance import routes  # noqa: E402,F401
