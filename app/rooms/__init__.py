"""
app/rooms/__init__.py
------------------------
Blueprint covering Room Management, Room Allocation, Room Transfer, and
Room Availability — grouped together since they all operate on the same
Room/RoomAllocation/RoomTransferRequest models.
"""

from flask import Blueprint

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

from app.rooms import routes  # noqa: E402,F401
