"""
app/models/visitor.py
------------------------
Tracks visitors who come to meet hostel students (gate register).
"""

from datetime import datetime

from app.extensions import db


class Visitor(db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    visitor_name = db.Column(db.String(120), nullable=False)
    relation = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    id_proof_type = db.Column(db.String(50), nullable=True)
    id_proof_number = db.Column(db.String(50), nullable=True)
    purpose = db.Column(db.String(255), nullable=True)

    check_in_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    check_out_time = db.Column(db.DateTime, nullable=True)

    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="visitors")
    approver = db.relationship("User", foreign_keys=[approved_by])

    @property
    def is_checked_out(self) -> bool:
        return self.check_out_time is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "roll_number": self.student.roll_number if self.student else None,
            "visitor_name": self.visitor_name,
            "relation": self.relation,
            "phone_number": self.phone_number,
            "id_proof_type": self.id_proof_type,
            "id_proof_number": self.id_proof_number,
            "purpose": self.purpose,
            "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
            "check_out_time": self.check_out_time.isoformat() if self.check_out_time else None,
            "is_checked_out": self.is_checked_out,
        }

    def __repr__(self) -> str:
        return f"<Visitor id={self.id} name={self.visitor_name}>"
