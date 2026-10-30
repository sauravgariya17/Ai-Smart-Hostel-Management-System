"""
app/ai/__init__.py
----------------------
Blueprint for Session 3 AI features: complaint classification, smart
room recommendations, occupancy forecasting, fee defaulter risk
prediction, and the hostel assistant chatbot.
"""

from flask import Blueprint

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

from app.ai import routes  # noqa: E402,F401
