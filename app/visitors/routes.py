"""
app/visitors/routes.py
--------------------------
Visitor Management: front-desk (warden/admin) checks visitors in and
out; students can view visitors who came to see them.
"""

from datetime import datetime

from flask import request, jsonify

from app.visitors import visitors_bp
from app.extensions import db
from app.models import Visitor, Student
from app.utils.decorators import admin_or_warden_required, student_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_filters, apply_date_range, apply_sort
from app.utils.validators import validate_required_fields


def _current_student_or_404():
    return Student.query.filter_by(user_id=get_current_user_id()).first()


@visitors_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_visitors():
    query = Visitor.query
    query = apply_search(query, Visitor, ["visitor_name", "phone_number"])
    query = apply_filters(query, Visitor, ["student_id"])
    query = apply_date_range(query, Visitor, "check_in_time")
    query = apply_sort(query, Visitor, ["id", "check_in_time"], default_field="check_in_time")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@visitors_bp.route("/active", methods=["GET"])
@admin_or_warden_required
def list_active_visitors():
    """Visitors currently inside the premises (not yet checked out)."""
    visitors = Visitor.query.filter(Visitor.check_out_time.is_(None)).order_by(Visitor.check_in_time.desc()).all()
    return jsonify({"success": True, "visitors": [v.to_dict() for v in visitors]}), 200


@visitors_bp.route("", methods=["POST"])
@admin_or_warden_required
def check_in_visitor():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["student_id", "visitor_name"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    student = Student.query.get(data["student_id"])
    if not student:
        return jsonify({"success": False, "message": "Invalid student_id."}), 404

    visitor = Visitor(
        student_id=student.id,
        visitor_name=data["visitor_name"].strip(),
        relation=data.get("relation"),
        phone_number=data.get("phone_number"),
        id_proof_type=data.get("id_proof_type"),
        id_proof_number=data.get("id_proof_number"),
        purpose=data.get("purpose"),
        approved_by=get_current_user_id(),
    )
    db.session.add(visitor)
    db.session.commit()

    return jsonify({"success": True, "message": "Visitor checked in.", "visitor": visitor.to_dict()}), 201


@visitors_bp.route("/<int:visitor_id>/check-out", methods=["PUT"])
@admin_or_warden_required
def check_out_visitor(visitor_id):
    visitor = Visitor.query.get(visitor_id)
    if not visitor:
        return jsonify({"success": False, "message": "Visitor record not found."}), 404

    if visitor.check_out_time:
        return jsonify({"success": False, "message": "Visitor has already been checked out."}), 409

    visitor.check_out_time = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True, "message": "Visitor checked out.", "visitor": visitor.to_dict()}), 200


@visitors_bp.route("/my", methods=["GET"])
@student_required
def my_visitors():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    visitors = Visitor.query.filter_by(student_id=student.id).order_by(Visitor.check_in_time.desc()).all()
    return jsonify({"success": True, "visitors": [v.to_dict() for v in visitors]}), 200
