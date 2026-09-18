"""
app/models/attendance.py
---------------------------
Daily hostel attendance, one row per student per calendar date.
"""

import enum
from datetime import datetime

from app.extensions import db


class AttendanceStatusEnum(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LEAVE = "leave"


class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("student_id", "attendance_date", name="uq_attendance_student_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.Enum(AttendanceStatusEnum), nullable=False, default=AttendanceStatusEnum.PRESENT)

    marked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="attendance_records")
    marker = db.relationship("User", foreign_keys=[marked_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "roll_number": self.student.roll_number if self.student else None,
            "attendance_date": self.attendance_date.isoformat() if self.attendance_date else None,
            "status": self.status.value if self.status else None,
            "remarks": self.remarks,
        }

    def __repr__(self) -> str:
        return f"<Attendance id={self.id} student_id={self.student_id} date={self.attendance_date}>"
