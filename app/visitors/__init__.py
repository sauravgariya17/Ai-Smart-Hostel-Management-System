"""
app/visitors/__init__.py
---------------------------
Blueprint for Visitor Management (gate register: check-in/check-out of
visitors meeting hostel students).
"""

from flask import Blueprint

visitors_bp = Blueprint("visitors", __name__, url_prefix="/api/visitors")

from app.visitors import routes  # noqa: E402,F401
