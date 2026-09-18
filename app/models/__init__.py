"""
app/models/__init__.py
------------------------
Aggregates all model classes so that:
  1. `from app.models import User, Student, Warden, ...` works cleanly.
  2. Flask-Migrate/Alembic can discover every table when generating
     migrations (models must be imported somewhere before `db.metadata`
     is inspected).
"""

from app.models.user import User, RoleEnum
from app.models.student import Student
from app.models.warden import Warden
from app.models.password_reset import PasswordResetToken
from app.models.token_blacklist import TokenBlacklist

from app.models.hostel import Hostel, Block, HostelTypeEnum
from app.models.room import (
    Room,
    RoomAllocation,
    RoomTransferRequest,
    RoomTypeEnum,
    RoomStatusEnum,
    AllocationStatusEnum,
    TransferStatusEnum,
)
from app.models.fee import FeeStructure, StudentFee, Payment, FeeStatusEnum, PaymentModeEnum
from app.models.visitor import Visitor
from app.models.attendance import Attendance, AttendanceStatusEnum
from app.models.complaint import (
    Complaint,
    ComplaintCategoryEnum,
    ComplaintPriorityEnum,
    ComplaintStatusEnum,
)
from app.models.maintenance import MaintenanceRequest, MaintenancePriorityEnum, MaintenanceStatusEnum
from app.models.notification import Notification, NotificationTypeEnum

__all__ = [
    "User",
    "RoleEnum",
    "Student",
    "Warden",
    "PasswordResetToken",
    "TokenBlacklist",
    "Hostel",
    "Block",
    "HostelTypeEnum",
    "Room",
    "RoomAllocation",
    "RoomTransferRequest",
    "RoomTypeEnum",
    "RoomStatusEnum",
    "AllocationStatusEnum",
    "TransferStatusEnum",
    "FeeStructure",
    "StudentFee",
    "Payment",
    "FeeStatusEnum",
    "PaymentModeEnum",
    "Visitor",
    "Attendance",
    "AttendanceStatusEnum",
    "Complaint",
    "ComplaintCategoryEnum",
    "ComplaintPriorityEnum",
    "ComplaintStatusEnum",
    "MaintenanceRequest",
    "MaintenancePriorityEnum",
    "MaintenanceStatusEnum",
    "Notification",
    "NotificationTypeEnum",
]
