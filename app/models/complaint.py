"""
app/models/complaint.py
--------------------------
Student complaints/grievances raised against hostel facilities or services,
triaged and resolved by wardens/admins.
"""

import enum
from datetime import datetime

from app.extensions import db


class ComplaintCategoryEnum(str, enum.Enum):
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CLEANLINESS = "cleanliness"
    INTERNET = "internet"
    FOOD = "food"
    SECURITY = "security"
    OTHER = "other"


class ComplaintPriorityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComplaintStatusEnum(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    category = db.Column(db.Enum(ComplaintCategoryEnum), nullable=False, default=ComplaintCategoryEnum.OTHER)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.Enum(ComplaintPriorityEnum), nullable=False, default=ComplaintPriorityEnum.MEDIUM)
    status = db.Column(db.Enum(ComplaintStatusEnum), nullable=False, default=ComplaintStatusEnum.OPEN)

    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolution_note = db.Column(db.String(500), nullable=True)

    # --- Session 3: AI Complaint Classification / Priority Prediction ---
    # Nullable, additive columns storing what the AI model suggested at
    # submission time, kept alongside (not instead of) the actual
    # category/priority so staff can compare AI vs. final human judgement.
    ai_suggested_category = db.Column(db.Enum(ComplaintCategoryEnum), nullable=True)
    ai_suggested_priority = db.Column(db.Enum(ComplaintPriorityEnum), nullable=True)
    ai_confidence = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="complaints")
    assignee = db.relationship("User", foreign_keys=[assigned_to])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "roll_number": self.student.roll_number if self.student else None,
            "category": self.category.value if self.category else None,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value if self.priority else None,
            "status": self.status.value if self.status else None,
            "assigned_to": self.assigned_to,
            "assigned_to_name": self.assignee.name if self.assignee else None,
            "resolution_note": self.resolution_note,
            "ai_suggested_category": self.ai_suggested_category.value if self.ai_suggested_category else None,
            "ai_suggested_priority": self.ai_suggested_priority.value if self.ai_suggested_priority else None,
            "ai_confidence": self.ai_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def __repr__(self) -> str:
        return f"<Complaint id={self.id} title={self.title}>"
