"""
app/models/student.py
----------------------
Student profile data, linked one-to-one with a User record (role=student).
"""

from datetime import datetime

from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    roll_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    course = db.Column(db.String(100), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)

    guardian_name = db.Column(db.String(120), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    # Placeholder for future room-allocation module (not part of today's foundation).
    room_id = db.Column(db.Integer, nullable=True)

    admission_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="student_profile")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "roll_number": self.roll_number,
            "course": self.course,
            "year_of_study": self.year_of_study,
            "phone_number": self.phone_number,
            "guardian_name": self.guardian_name,
            "guardian_phone": self.guardian_phone,
            "address": self.address,
            "room_id": self.room_id,
            "admission_date": self.admission_date.isoformat() if self.admission_date else None,
        }

    def __repr__(self) -> str:
        return f"<Student id={self.id} roll_number={self.roll_number}>"
