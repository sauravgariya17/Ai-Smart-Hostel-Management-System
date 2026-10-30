"""
app/students/routes.py
--------------------------
Student Management endpoints for admins/wardens, plus a self-service
"my profile" endpoint for the logged-in student.
"""

from datetime import datetime, date

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app.students import students_bp
from app.extensions import db
from app.models import User, RoleEnum, Student, RoomAllocation, AllocationStatusEnum, StudentFee, Complaint
from app.utils.decorators import admin_required, admin_or_warden_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_filters, apply_sort
from app.utils.validators import validate_required_fields, is_valid_email, is_strong_password


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@students_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_students():
    query = Student.query.join(User, Student.user_id == User.id)

    query = apply_search(query, Student, ["roll_number"])
    query = apply_filters(query, Student, ["course"])
    query = apply_sort(query, Student, ["id", "roll_number", "year_of_study"], default_field="id")

    result = paginate_query(query, serializer=lambda s: s.user.to_dict(include_profile=True))
    return jsonify({"success": True, **result}), 200


@students_bp.route("/<int:student_id>", methods=["GET"])
@admin_or_warden_required
def get_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404
    return jsonify({"success": True, "student": student.user.to_dict(include_profile=True)}), 200


@students_bp.route("", methods=["POST"])
@admin_required
def create_student():
    """Admin-initiated student onboarding (as opposed to public self-registration)."""
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "roll_number"]
    errors = validate_required_fields(data, required)

    email = (data.get("email") or "").lower().strip()
    if email and not is_valid_email(email):
        errors.append("A valid email address is required.")

    password = data.get("password", "")
    if password and not is_strong_password(password):
        errors.append("Password must include uppercase, lowercase, digit, and special character (min 8 chars).")

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email is already registered."}), 409

    roll_number = data["roll_number"].strip()
    if Student.query.filter_by(roll_number=roll_number).first():
        return jsonify({"success": False, "message": "Roll number is already registered."}), 409

    user = User(name=data["name"].strip(), email=email, role=RoleEnum.STUDENT, is_active=True, is_verified=True)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    student = Student(
        user_id=user.id,
        roll_number=roll_number,
        course=data.get("course"),
        year_of_study=data.get("year_of_study"),
        phone_number=data.get("phone_number"),
        guardian_name=data.get("guardian_name"),
        guardian_phone=data.get("guardian_phone"),
        address=data.get("address"),
        admission_date=_parse_date(data.get("admission_date")) or date.today(),
    )
    db.session.add(student)
    db.session.commit()

    return jsonify({"success": True, "message": "Student created successfully.", "student": user.to_dict(include_profile=True)}), 201


@students_bp.route("/<int:student_id>", methods=["PUT"])
@admin_or_warden_required
def update_student(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    data = request.get_json(silent=True) or {}

    if "name" in data and data["name"]:
        student.user.name = data["name"].strip()

    for field in ["course", "phone_number", "guardian_name", "guardian_phone", "address"]:
        if field in data:
            setattr(student, field, data[field])

    if "year_of_study" in data:
        student.year_of_study = data["year_of_study"]

    if "is_active" in data:
        student.user.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify({"success": True, "message": "Student updated successfully.", "student": student.user.to_dict(include_profile=True)}), 200


@students_bp.route("/<int:student_id>", methods=["DELETE"])
@admin_required
def deactivate_student(student_id):
    """Soft-delete: deactivate the student's account rather than hard-deleting records."""
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    student.user.is_active = False
    db.session.commit()
    return jsonify({"success": True, "message": "Student account deactivated."}), 200


@students_bp.route("/<int:student_id>/summary", methods=["GET"])
@jwt_required()
def student_summary(student_id):
    """Room, fee balance, and complaint counts for a single student —
    used by both the admin/warden student-detail view and the student's
    own dashboard."""
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    active_allocation = RoomAllocation.query.filter_by(
        student_id=student.id, status=AllocationStatusEnum.ACTIVE
    ).first()

    pending_fees = StudentFee.query.filter(StudentFee.student_id == student.id, StudentFee.status != "paid").all()
    total_due = sum(fee.balance for fee in pending_fees)

    open_complaints = Complaint.query.filter(
        Complaint.student_id == student.id, Complaint.status.in_(["open", "in_progress"])
    ).count()

    return jsonify({
        "success": True,
        "summary": {
            "student": student.user.to_dict(include_profile=True),
            "room": active_allocation.room.to_dict() if active_allocation else None,
            "total_fee_due": total_due,
            "open_complaints": open_complaints,
        },
    }), 200
