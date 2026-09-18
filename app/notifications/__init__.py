"""
app/notifications/__init__.py
---------------------------------
Blueprint for the Notification System: personal + role-broadcast
in-app notifications.
"""

from flask import Blueprint

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

from app.notifications import routes  # noqa: E402,F401
