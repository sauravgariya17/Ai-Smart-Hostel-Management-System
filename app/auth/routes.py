"""
app/auth/routes.py
---------------------
All authentication endpoints for the AI-Powered Smart Hostel Management
System:

    Admin    : register (admin-only), login
    Student  : self-register, login
    Warden   : register (admin-only), login
    Shared   : refresh, logout, forgot-password, reset-password, me

JWT access tokens embed a `role` custom claim which the RBAC decorators
in app/utils/decorators.py inspect to authorize protected endpoints.
"""

from datetime import datetime, date

from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity,
)

from app.auth import auth_bp
from app.extensions import db
from app.models import User, RoleEnum, Student, Warden, PasswordResetToken, TokenBlacklist
from app.utils.decorators import admin_required, get_current_user_id
from app.utils.validators import validate_registration_payload, validate_login_payload
from app.utils.email_utils import send_password_reset_email


# ======================================================================
# Internal helpers
# ======================================================================

def _issue_tokens(user: User) -> dict:
    """Create a matched access/refresh token pair carrying the user's role."""
    identity = str(user.id)
    additional_claims = {"role": user.role.value, "email": user.email, "name": user.name}

    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)

    return {"access_token": access_token, "refresh_token": refresh_token}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ======================================================================
# ADMIN AUTHENTICATION
# ======================================================================

@auth_bp.route("/admin/register", methods=["POST"])
@admin_required
def register_admin():
    """Create a new admin account. Restricted to existing admins so the
    first admin must be created via the seed_admin.py CLI script."""
    data = request.get_json(silent=True) or {}
    errors = validate_registration_payload(data, ["name", "email", "password"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if User.query.filter_by(email=data["email"].lower().strip()).first():
        return jsonify({"success": False, "message": "Email is already registered."}), 409

    admin_user = User(
        name=data["name"].strip(),
        email=data["email"].lower().strip(),
        role=RoleEnum.ADMIN,
        is_active=True,
        is_verified=True,
    )
    admin_user.set_password(data["password"])

    db.session.add(admin_user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Admin account created successfully.",
        "user": admin_user.to_dict(),
    }), 201


@auth_bp.route("/admin/login", methods=["POST"])
def login_admin():
    return _handle_login(expected_role=RoleEnum.ADMIN)


# ======================================================================
# STUDENT AUTHENTICATION
# ======================================================================

@auth_bp.route("/student/register", methods=["POST"])
def register_student():
    """Public self-registration endpoint for students."""
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "roll_number"]
    errors = validate_registration_payload(data, required)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    email = data["email"].lower().strip()
    roll_number = data["roll_number"].strip()

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email is already registered."}), 409

    if Student.query.filter_by(roll_number=roll_number).first():
        return jsonify({"success": False, "message": "Roll number is already registered."}), 409

    student_user = User(
        name=data["name"].strip(),
        email=email,
        role=RoleEnum.STUDENT,
        is_active=True,
        is_verified=False,
    )
    student_user.set_password(data["password"])
    db.session.add(student_user)
    db.session.flush()  # obtain student_user.id before commit

    student_profile = Student(
        user_id=student_user.id,
        roll_number=roll_number,
        course=data.get("course"),
        year_of_study=data.get("year_of_study"),
        phone_number=data.get("phone_number"),
        guardian_name=data.get("guardian_name"),
        guardian_phone=data.get("guardian_phone"),
        address=data.get("address"),
        admission_date=_parse_date(data.get("admission_date")) or date.today(),
    )
    db.session.add(student_profile)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Student registered successfully.",
        "user": student_user.to_dict(include_profile=True),
    }), 201


@auth_bp.route("/student/login", methods=["POST"])
def login_student():
    return _handle_login(expected_role=RoleEnum.STUDENT)


# ======================================================================
# WARDEN AUTHENTICATION
# ======================================================================

@auth_bp.route("/warden/register", methods=["POST"])
@admin_required
def register_warden():
    """Wardens are onboarded by an admin, not self-registered."""
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "employee_id"]
    errors = validate_registration_payload(data, required)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    email = data["email"].lower().strip()
    employee_id = data["employee_id"].strip()

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email is already registered."}), 409

    if Warden.query.filter_by(employee_id=employee_id).first():
        return jsonify({"success": False, "message": "Employee ID is already registered."}), 409

    warden_user = User(
        name=data["name"].strip(),
        email=email,
        role=RoleEnum.WARDEN,
        is_active=True,
        is_verified=True,
    )
    warden_user.set_password(data["password"])
    db.session.add(warden_user)
    db.session.flush()

    warden_profile = Warden(
        user_id=warden_user.id,
        employee_id=employee_id,
        phone_number=data.get("phone_number"),
        assigned_block=data.get("assigned_block"),
        designation=data.get("designation", "Warden"),
        joining_date=_parse_date(data.get("joining_date")) or date.today(),
    )
    db.session.add(warden_profile)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Warden registered successfully.",
        "user": warden_user.to_dict(include_profile=True),
    }), 201


@auth_bp.route("/warden/login", methods=["POST"])
def login_warden():
    return _handle_login(expected_role=RoleEnum.WARDEN)


# ======================================================================
# SHARED LOGIN LOGIC
# ======================================================================

def _handle_login(expected_role: RoleEnum):
    data = request.get_json(silent=True) or {}
    errors = validate_login_payload(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    email = data["email"].lower().strip()
    password = data["password"]

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    if user.role != expected_role:
        return jsonify({
            "success": False,
            "message": f"This account is not registered as a {expected_role.value}."
        }), 403

    if not user.is_active:
        return jsonify({"success": False, "message": "Your account has been deactivated. Contact the admin."}), 403

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    tokens = _issue_tokens(user)

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user.to_dict(include_profile=True),
        **tokens,
    }), 200


# ======================================================================
# SHARED: REFRESH / LOGOUT / ME
# ======================================================================

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    """Exchange a valid refresh token for a new access token."""
    identity = get_jwt_identity()
    claims = get_jwt()

    additional_claims = {
        "role": claims.get("role"),
        "email": claims.get("email"),
        "name": claims.get("name"),
    }
    new_access_token = create_access_token(identity=identity, additional_claims=additional_claims)

    return jsonify({"success": True, "access_token": new_access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Revoke the current access token by recording its jti in the blacklist."""
    jwt_data = get_jwt()
    blacklisted = TokenBlacklist(
        jti=jwt_data["jti"],
        token_type=jwt_data["type"],
        user_id=int(get_jwt_identity()),
    )
    db.session.add(blacklisted)
    db.session.commit()

    return jsonify({"success": True, "message": "Logged out successfully."}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = User.query.get(get_current_user_id())
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    return jsonify({"success": True, "user": user.to_dict(include_profile=True)}), 200


# ======================================================================
# FORGOT PASSWORD / RESET PASSWORD
# ======================================================================

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Always responds with a generic success message (whether or not the
    email exists) to avoid leaking which emails are registered.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").lower().strip()

    generic_response = {
        "success": True,
        "message": "If an account with that email exists, a password reset link has been sent."
    }

    if not email:
        return jsonify({"success": False, "message": "'email' is required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(generic_response), 200

    expiry_minutes = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", 60)
    token_record, raw_token = PasswordResetToken.generate_token(
        user_id=user.id, expires_in_minutes=expiry_minutes
    )
    db.session.add(token_record)
    db.session.commit()

    reset_base_url = current_app.config.get("FRONTEND_RESET_PASSWORD_URL")
    reset_link = f"{reset_base_url}?token={raw_token}"

    try:
        send_password_reset_email(to_email=user.email, reset_link=reset_link, user_name=user.name)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error("Failed to send password reset email: %s", exc)

    return jsonify(generic_response), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    raw_token = data.get("token")
    new_password = data.get("new_password")

    if not raw_token or not new_password:
        return jsonify({
            "success": False,
            "message": "'token' and 'new_password' are required."
        }), 400

    from app.utils.validators import is_strong_password
    if not is_strong_password(new_password):
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters and include an uppercase letter, "
                        "a lowercase letter, a digit, and a special character."
        }), 400

    token_record = PasswordResetToken.find_valid_token(raw_token)
    if not token_record:
        return jsonify({"success": False, "message": "Invalid or expired reset token."}), 400

    user = User.query.get(token_record.user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    user.set_password(new_password)
    token_record.mark_used()
    db.session.commit()

    return jsonify({"success": True, "message": "Password has been reset successfully. You may now log in."}), 200
