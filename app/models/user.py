"""
app/models/user.py
-------------------
Core User model. Every person who can log in to the system (Admin,
Student, Warden) has exactly one row here. Role-specific data lives in
their own profile tables (Student, Warden) linked back to this table
via a one-to-one foreign key relationship.
"""

import enum
from datetime import datetime

from app.extensions import db, bcrypt


class RoleEnum(str, enum.Enum):
    """Enumeration of all valid system roles used for RBAC checks."""
    ADMIN = "admin"
    STUDENT = "student"
    WARDEN = "warden"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False, index=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # One-to-one relationships to role-specific profile tables.
    student_profile = db.relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    warden_profile = db.relationship(
        "Warden", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    reset_tokens = db.relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )

    # ---------------- Password Helpers ----------------
    def set_password(self, raw_password: str) -> None:
        """Hash and store the given plaintext password."""
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    # ---------------- Serialization ----------------
    def to_dict(self, include_profile: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value if isinstance(self.role, RoleEnum) else self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_profile:
            if self.role == RoleEnum.STUDENT and self.student_profile:
                data["profile"] = self.student_profile.to_dict()
            elif self.role == RoleEnum.WARDEN and self.warden_profile:
                data["profile"] = self.warden_profile.to_dict()
        return data

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
