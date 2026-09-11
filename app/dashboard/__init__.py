"""
app/dashboard/__init__.py
-----------------------------
Blueprint serving role-specific dashboard statistics (Admin Dashboard,
Warden Dashboard, Student Dashboard) consumed by the dashboard templates
and Chart.js widgets.
"""

from flask import Blueprint

dashboard_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")

from app.dashboard import routes  # noqa: E402,F401
