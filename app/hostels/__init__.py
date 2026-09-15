"""
app/hostels/__init__.py
--------------------------
Blueprint for Hostel Management (hostels + blocks). Admin-only writes;
reads open to any authenticated staff role.
"""

from flask import Blueprint

hostels_bp = Blueprint("hostels", __name__, url_prefix="/api/hostels")

from app.hostels import routes  # noqa: E402,F401
