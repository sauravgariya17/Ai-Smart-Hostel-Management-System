"""
app/models/notification.py
------------------------------
In-app notifications. A notification is either:
  - Personal:   user_id is set    -> shown only to that user.
  - Broadcast:  target_role is set (user_id NULL) -> shown to every user
                with that role (e.g. announce to all students).
"""

import enum
from datetime import datetime

from app.extensions import db


class NotificationTypeEnum(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    target_role = db.Column(db.String(20), nullable=True)  # 'admin' | 'warden' | 'student' | None

    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    notif_type = db.Column(db.Enum(NotificationTypeEnum), nullable=False, default=NotificationTypeEnum.INFO)

    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_role": self.target_role,
            "title": self.title,
            "message": self.message,
            "notif_type": self.notif_type.value if self.notif_type else None,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Notification id={self.id} title={self.title}>"
