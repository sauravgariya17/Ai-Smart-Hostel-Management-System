"""
app/complaints/__init__.py
------------------------------
Blueprint for Complaint Management (student grievances raised against
hostel facilities/services, triaged by wardens/admins).
"""

from flask import Blueprint

complaints_bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")

from app.complaints import routes  # noqa: E402,F401
