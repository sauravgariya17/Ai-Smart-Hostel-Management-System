"""
Warden management endpoints.

Admins can create, edit, deactivate, and list warden accounts.
Wardens are normal User records with role=warden plus a Warden profile.
"""

from datetime import datetime

from flask import request, jsonify

from app.wardens import wardens_bp
from app.extensions import db
from app.models import User, Warden, RoleEnum
from app.utils.decorators import admin_required, admin_or_warden_required
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_sort
from app.utils.validators import validate_required_fields, is_valid_email, is_strong_password


def _serialize(warden):
    data = warden.user.to_dict(include_profile=True)
    data["profile_id"] = warden.id
    data["employee_id"] = warden.employee_id
    data["phone_number"] = warden.phone_number
    data["assigned_block"] = warden.assigned_block
    data["designation"] = warden.designation
    data["joining_date"] = warden.joining_date.isoformat() if warden.joining_date else None
    return data


@wardens_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_wardens():
    query = Warden.query.join(User, Warden.user_id == User.id)
    query = apply_search(query, User, ["name", "email"])
    query = apply_sort(query, Warden, ["id", "employee_id"], default_field="id")
    result = paginate_query(query, serializer=_serialize)
    return jsonify({"success": True, **result}), 200


@wardens_bp.route("", methods=["POST"])
@admin_required
def create_warden():
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "employee_id"]
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

    employee_id = str(data["employee_id"]).strip()
    if Warden.query.filter_by(employee_id=employee_id).first():
        return jsonify({"success": False, "message": "Employee ID is already registered."}), 409

    user = User(
        name=str(data["name"]).strip(),
        email=email,
        role=RoleEnum.WARDEN,
        is_active=True,
        is_verified=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    joining_date = None
    if data.get("joining_date"):
        try:
            joining_date = datetime.strptime(data["joining_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "joining_date must be YYYY-MM-DD."}), 400

    warden = Warden(
        user_id=user.id,
        employee_id=employee_id,
        phone_number=data.get("phone_number"),
        assigned_block=data.get("assigned_block"),
        designation=data.get("designation") or "Warden",
        joining_date=joining_date,
    )
    db.session.add(warden)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Warden created successfully.",
        "warden": _serialize(warden),
    }), 201


@wardens_bp.route("/<int:warden_id>", methods=["PUT"])
@admin_required
def update_warden(warden_id):
    warden = Warden.query.get(warden_id)
    if not warden:
        return jsonify({"success": False, "message": "Warden not found."}), 404

    data = request.get_json(silent=True) or {}

    if "name" in data and data["name"]:
        warden.user.name = str(data["name"]).strip()

    if "email" in data and data["email"]:
        email = str(data["email"]).lower().strip()
        if not is_valid_email(email):
            return jsonify({"success": False, "message": "A valid email address is required."}), 400
        existing = User.query.filter(User.email == email, User.id != warden.user_id).first()
        if existing:
            return jsonify({"success": False, "message": "Email is already registered."}), 409
        warden.user.email = email

    if "employee_id" in data and data["employee_id"]:
        employee_id = str(data["employee_id"]).strip()
        existing = Warden.query.filter(
            Warden.employee_id == employee_id, Warden.id != warden.id
        ).first()
        if existing:
            return jsonify({"success": False, "message": "Employee ID is already registered."}), 409
        warden.employee_id = employee_id

    for field in ["phone_number", "assigned_block", "designation"]:
        if field in data:
            setattr(warden, field, data[field])

    if "joining_date" in data:
        try:
            warden.joining_date = (
                datetime.strptime(data["joining_date"], "%Y-%m-%d").date()
                if data["joining_date"] else None
            )
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "joining_date must be YYYY-MM-DD."}), 400

    if data.get("password"):
        password = data["password"]
        if not is_strong_password(password):
            return jsonify({"success": False, "message": "Password must include uppercase, lowercase, digit, and special character (min 8 chars)."}), 400
        warden.user.set_password(password)

    if "is_active" in data:
        warden.user.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify({"success": True, "message": "Warden updated successfully.", "warden": _serialize(warden)}), 200


@wardens_bp.route("/<int:warden_id>", methods=["DELETE"])
@admin_required
def deactivate_warden(warden_id):
    warden = Warden.query.get(warden_id)
    if not warden:
        return jsonify({"success": False, "message": "Warden not found."}), 404

    warden.user.is_active = False
    db.session.commit()
    return jsonify({"success": True, "message": "Warden account deactivated."}), 200
