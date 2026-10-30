"""
app/students/__init__.py
---------------------------
Blueprint for Student Management (admin/warden CRUD over student
profiles, distinct from the self-service /api/auth/student/register
used for public sign-up).
"""

from flask import Blueprint

students_bp = Blueprint("students", __name__, url_prefix="/api/students")

from app.students import routes  # noqa: E402,F401
