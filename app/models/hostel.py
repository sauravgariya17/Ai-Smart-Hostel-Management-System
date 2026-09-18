"""
app/models/hostel.py
-----------------------
Hostel and Block models. A Hostel is a physical building (e.g. "Boys
Hostel - A", "Girls Hostel - B"); a Block is a wing/section within a
hostel (e.g. "Block A", "Block B") used to group rooms and assign
wardens to specific areas.
"""

import enum
from datetime import datetime

from app.extensions import db


class HostelTypeEnum(str, enum.Enum):
    BOYS = "boys"
    GIRLS = "girls"
    CO_ED = "co_ed"


class Hostel(db.Model):
    __tablename__ = "hostels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    hostel_type = db.Column(db.Enum(HostelTypeEnum), nullable=False, default=HostelTypeEnum.CO_ED)
    address = db.Column(db.String(255), nullable=True)
    total_floors = db.Column(db.Integer, nullable=True, default=1)
    warden_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    blocks = db.relationship("Block", back_populates="hostel", cascade="all, delete-orphan")
    rooms = db.relationship("Room", back_populates="hostel", cascade="all, delete-orphan")
    warden = db.relationship("User", foreign_keys=[warden_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hostel_type": self.hostel_type.value if self.hostel_type else None,
            "address": self.address,
            "total_floors": self.total_floors,
            "warden_id": self.warden_id,
            "warden_name": self.warden.name if self.warden else None,
            "total_rooms": len(self.rooms) if self.rooms else 0,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Hostel id={self.id} name={self.name}>"


class Block(db.Model):
    __tablename__ = "blocks"
    __table_args__ = (db.UniqueConstraint("hostel_id", "name", name="uq_block_hostel_name"),)

    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    total_floors = db.Column(db.Integer, nullable=True, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    hostel = db.relationship("Hostel", back_populates="blocks")
    rooms = db.relationship("Room", back_populates="block")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hostel_id": self.hostel_id,
            "hostel_name": self.hostel.name if self.hostel else None,
            "name": self.name,
            "total_floors": self.total_floors,
        }

    def __repr__(self) -> str:
        return f"<Block id={self.id} name={self.name}>"
