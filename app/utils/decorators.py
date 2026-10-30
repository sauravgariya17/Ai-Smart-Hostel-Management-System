"""
app/utils/decorators.py
--------------------------
Role-Based Access Control (RBAC) decorators.

These wrap Flask-JWT-Extended's `jwt_required()` and additionally
inspect the "role" custom claim embedded in the access token (see
app/auth/routes.py where tokens are issued with `additional_claims`).

Usage:
    @admin_required
    def some_admin_only_view(): ...

    @role_required("warden", "admin")
    def some_shared_view(): ...
"""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity


def role_required(*allowed_roles: str):
    """Generic decorator: allow access only if the JWT's role claim is
    one of `allowed_roles`. Must be used on routes that also require a
    valid JWT (it performs verification itself)."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")

            if user_role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": "You do not have permission to access this resource."
                }), 403

            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_func):
    return role_required("admin")(view_func)


def warden_required(view_func):
    return role_required("warden")(view_func)


def student_required(view_func):
    return role_required("student")(view_func)


def admin_or_warden_required(view_func):
    return role_required("admin", "warden")(view_func)


def get_current_user_id() -> int:
    """Convenience helper to fetch the authenticated user's integer id
    from the JWT identity (identity is always stored as a string)."""
    identity = get_jwt_identity()
    return int(identity) if identity is not None else None
