"""
app/models/fee.py
--------------------
Fee Management & Payment History models.

FeeStructure  : master rent/fee rates defined by admin (per room type / year).
StudentFee    : an individual invoice raised for a student for a period.
Payment       : one payment transaction applied against a StudentFee invoice
                (supports partial payments; a single invoice can have many).
"""

import enum
from datetime import datetime

from app.extensions import db


class FeeStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"


class PaymentModeEnum(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"

    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id", ondelete="SET NULL"), nullable=True)
    room_type = db.Column(db.String(20), nullable=True)
    academic_year = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    hostel = db.relationship("Hostel")
    student_fees = db.relationship("StudentFee", back_populates="fee_structure")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hostel_id": self.hostel_id,
            "hostel_name": self.hostel.name if self.hostel else "All Hostels",
            "room_type": self.room_type,
            "academic_year": self.academic_year,
            "amount": float(self.amount) if self.amount is not None else 0,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<FeeStructure id={self.id} year={self.academic_year} amount={self.amount}>"


class StudentFee(db.Model):
    __tablename__ = "student_fees"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey("fee_structures.id"), nullable=True)

    academic_year = db.Column(db.String(20), nullable=False)
    billing_month = db.Column(db.String(20), nullable=True)  # e.g. "January"
    amount_due = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(FeeStatusEnum), nullable=False, default=FeeStatusEnum.PENDING)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="fee_invoices")
    fee_structure = db.relationship("FeeStructure", back_populates="student_fees")
    payments = db.relationship("Payment", back_populates="student_fee", cascade="all, delete-orphan")

    @property
    def balance(self):
        return float(self.amount_due) - float(self.amount_paid)

    def refresh_status(self) -> None:
        if float(self.amount_paid) <= 0:
            self.status = FeeStatusEnum.OVERDUE if self.due_date < datetime.utcnow().date() else FeeStatusEnum.PENDING
        elif float(self.amount_paid) >= float(self.amount_due):
            self.status = FeeStatusEnum.PAID
        else:
            self.status = FeeStatusEnum.PARTIAL

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "roll_number": self.student.roll_number if self.student else None,
            "academic_year": self.academic_year,
            "billing_month": self.billing_month,
            "amount_due": float(self.amount_due) if self.amount_due is not None else 0,
            "amount_paid": float(self.amount_paid) if self.amount_paid is not None else 0,
            "balance": self.balance,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value if self.status else None,
        }

    def __repr__(self) -> str:
        return f"<StudentFee id={self.id} student_id={self.student_id} status={self.status}>"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    student_fee_id = db.Column(db.Integer, db.ForeignKey("student_fees.id", ondelete="CASCADE"), nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_mode = db.Column(db.Enum(PaymentModeEnum), nullable=False, default=PaymentModeEnum.CASH)
    transaction_reference = db.Column(db.String(120), nullable=True)
    remarks = db.Column(db.String(255), nullable=True)

    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    received_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    student_fee = db.relationship("StudentFee", back_populates="payments")
    receiver = db.relationship("User", foreign_keys=[received_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_fee_id": self.student_fee_id,
            "student_name": (
                self.student_fee.student.user.name
                if self.student_fee and self.student_fee.student and self.student_fee.student.user
                else None
            ),
            "amount": float(self.amount) if self.amount is not None else 0,
            "payment_mode": self.payment_mode.value if self.payment_mode else None,
            "transaction_reference": self.transaction_reference,
            "remarks": self.remarks,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "received_by_name": self.receiver.name if self.receiver else None,
        }

    def __repr__(self) -> str:
        return f"<Payment id={self.id} amount={self.amount}>"
