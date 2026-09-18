"""
app/models/room.py
---------------------
Room inventory plus the two workflows built on top of it:
  - RoomAllocation: assigning a student to a room (and vacating them).
  - RoomTransferRequest: a student requesting to move to a different room,
    subject to admin/warden approval.
"""

import enum
from datetime import datetime

from app.extensions import db


class RoomTypeEnum(str, enum.Enum):
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    DORMITORY = "dormitory"


class RoomStatusEnum(str, enum.Enum):
    AVAILABLE = "available"
    FULL = "full"
    MAINTENANCE = "maintenance"


class Room(db.Model):
    __tablename__ = "rooms"
    __table_args__ = (
        db.UniqueConstraint("hostel_id", "room_number", name="uq_room_hostel_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    block_id = db.Column(db.Integer, db.ForeignKey("blocks.id", ondelete="SET NULL"), nullable=True)

    room_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer, nullable=True, default=1)
    room_type = db.Column(db.Enum(RoomTypeEnum), nullable=False, default=RoomTypeEnum.DOUBLE)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    occupied_beds = db.Column(db.Integer, nullable=False, default=0)
    monthly_rent = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.Enum(RoomStatusEnum), nullable=False, default=RoomStatusEnum.AVAILABLE)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    hostel = db.relationship("Hostel", back_populates="rooms")
    block = db.relationship("Block", back_populates="rooms")
    allocations = db.relationship("RoomAllocation", back_populates="room", cascade="all, delete-orphan")

    @property
    def available_beds(self) -> int:
        return max(self.capacity - self.occupied_beds, 0)

    def refresh_status(self) -> None:
        """Recompute the room's status from its current occupancy.
        Does not override an explicit MAINTENANCE flag set by staff."""
        if self.status == RoomStatusEnum.MAINTENANCE:
            return
        self.status = RoomStatusEnum.FULL if self.occupied_beds >= self.capacity else RoomStatusEnum.AVAILABLE

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hostel_id": self.hostel_id,
            "hostel_name": self.hostel.name if self.hostel else None,
            "block_id": self.block_id,
            "block_name": self.block.name if self.block else None,
            "room_number": self.room_number,
            "floor": self.floor,
            "room_type": self.room_type.value if self.room_type else None,
            "capacity": self.capacity,
            "occupied_beds": self.occupied_beds,
            "available_beds": self.available_beds,
            "monthly_rent": float(self.monthly_rent) if self.monthly_rent is not None else 0,
            "status": self.status.value if self.status else None,
        }

    def __repr__(self) -> str:
        return f"<Room id={self.id} number={self.room_number}>"


class AllocationStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    VACATED = "vacated"


class RoomAllocation(db.Model):
    __tablename__ = "room_allocations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)

    allocated_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    vacated_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.Enum(AllocationStatusEnum), nullable=False, default=AllocationStatusEnum.ACTIVE)

    allocated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="room_allocations")
    room = db.relationship("Room", back_populates="allocations")
    allocator = db.relationship("User", foreign_keys=[allocated_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "roll_number": self.student.roll_number if self.student else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "hostel_name": self.room.hostel.name if self.room and self.room.hostel else None,
            "allocated_date": self.allocated_date.isoformat() if self.allocated_date else None,
            "vacated_date": self.vacated_date.isoformat() if self.vacated_date else None,
            "status": self.status.value if self.status else None,
            "remarks": self.remarks,
        }

    def __repr__(self) -> str:
        return f"<RoomAllocation id={self.id} student_id={self.student_id} room_id={self.room_id}>"


class TransferStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RoomTransferRequest(db.Model):
    __tablename__ = "room_transfer_requests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    current_room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True)
    requested_room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)

    reason = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(TransferStatusEnum), nullable=False, default=TransferStatusEnum.PENDING)

    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.String(255), nullable=True)

    student = db.relationship("Student", backref="transfer_requests")
    current_room = db.relationship("Room", foreign_keys=[current_room_id])
    requested_room = db.relationship("Room", foreign_keys=[requested_room_id])
    processor = db.relationship("User", foreign_keys=[processed_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.name if self.student and self.student.user else None,
            "current_room_number": self.current_room.room_number if self.current_room else None,
            "requested_room_id": self.requested_room_id,
            "requested_room_number": self.requested_room.room_number if self.requested_room else None,
            "reason": self.reason,
            "status": self.status.value if self.status else None,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "remarks": self.remarks,
        }

    def __repr__(self) -> str:
        return f"<RoomTransferRequest id={self.id} student_id={self.student_id}>"
