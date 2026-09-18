"""
app/models/warden.py
---------------------
Warden profile data, linked one-to-one with a User record (role=warden).
"""

from datetime import datetime

from app.extensions import db


class Warden(db.Model):
    __tablename__ = "wardens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    employee_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    phone_number = db.Column(db.String(20), nullable=True)
    assigned_block = db.Column(db.String(50), nullable=True)
    designation = db.Column(db.String(100), nullable=True, default="Warden")

    joining_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="warden_profile")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "phone_number": self.phone_number,
            "assigned_block": self.assigned_block,
            "designation": self.designation,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
        }

    def __repr__(self) -> str:
        return f"<Warden id={self.id} employee_id={self.employee_id}>"
