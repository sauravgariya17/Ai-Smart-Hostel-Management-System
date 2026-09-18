"""
app/models/maintenance.py
----------------------------
Maintenance/repair work orders raised against rooms or common hostel
infrastructure (distinct from student Complaints — these are typically
raised or triaged by wardens/admins as actionable work items).
"""

import enum
from datetime import datetime

from app.extensions import db


class MaintenancePriorityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MaintenanceStatusEnum(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    reported_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    category = db.Column(db.String(80), nullable=False, default="general")
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.Enum(MaintenancePriorityEnum), nullable=False, default=MaintenancePriorityEnum.MEDIUM)
    status = db.Column(db.Enum(MaintenanceStatusEnum), nullable=False, default=MaintenanceStatusEnum.PENDING)

    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    room = db.relationship("Room", backref="maintenance_requests")
    reporter = db.relationship("User", foreign_keys=[reported_by])
    assignee = db.relationship("User", foreign_keys=[assigned_to])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "reported_by": self.reported_by,
            "reported_by_name": self.reporter.name if self.reporter else None,
            "category": self.category,
            "description": self.description,
            "priority": self.priority.value if self.priority else None,
            "status": self.status.value if self.status else None,
            "assigned_to": self.assigned_to,
            "assigned_to_name": self.assignee.name if self.assignee else None,
            "cost": float(self.cost) if self.cost is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self) -> str:
        return f"<MaintenanceRequest id={self.id} status={self.status}>"
