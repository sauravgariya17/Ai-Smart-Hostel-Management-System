"""
app/complaints/routes.py
----------------------------
Complaint Management: students raise complaints; wardens/admins triage,
assign, and resolve them.
"""

from datetime import datetime

from flask import request, jsonify

from app.complaints import complaints_bp
from app.extensions import db
from app.models import Complaint, ComplaintCategoryEnum, ComplaintPriorityEnum, ComplaintStatusEnum, Student
from app.utils.decorators import admin_or_warden_required, student_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_filters, apply_sort
from app.utils.validators import validate_required_fields, validate_choice
from app.utils.notify import notify_role, notify_user
from app.ai.services.complaint_classifier import classify_complaint

CATEGORIES = [e.value for e in ComplaintCategoryEnum]
PRIORITIES = [e.value for e in ComplaintPriorityEnum]
STATUSES = [e.value for e in ComplaintStatusEnum]


def _current_student_or_404():
    return Student.query.filter_by(user_id=get_current_user_id()).first()


@complaints_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_complaints():
    query = Complaint.query
    query = apply_search(query, Complaint, ["title"])
    query = apply_filters(query, Complaint, ["status", "category", "priority", "assigned_to", "student_id"])
    query = apply_sort(query, Complaint, ["id", "created_at", "priority"], default_field="created_at")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@complaints_bp.route("/<int:complaint_id>", methods=["GET"])
@admin_or_warden_required
def get_complaint(complaint_id):
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"success": False, "message": "Complaint not found."}), 404
    return jsonify({"success": True, "complaint": complaint.to_dict()}), 200


@complaints_bp.route("", methods=["POST"])
@student_required
def raise_complaint():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["title"])
    if "category" in data and data["category"]:
        errors += validate_choice(data.get("category"), CATEGORIES, "category")
    if "priority" in data and data["priority"]:
        errors += validate_choice(data.get("priority"), PRIORITIES, "priority")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    # --- Session 3: AI Complaint Classification + Priority Prediction ---
    # Always compute an AI suggestion for transparency (stored alongside the
    # final values so staff can compare); if the student didn't pick a
    # category/priority themselves, fall back to the AI's suggestion instead
    # of a hardcoded default.
    ai_prediction = classify_complaint(title=data.get("title", ""), description=data.get("description", ""))

    final_category = data.get("category") or ai_prediction["predicted_category"]
    final_priority = data.get("priority") or ai_prediction["predicted_priority"]

    complaint = Complaint(
        student_id=student.id,
        category=final_category,
        title=data["title"].strip(),
        description=data.get("description"),
        priority=final_priority,
        status=ComplaintStatusEnum.OPEN,
        ai_suggested_category=ai_prediction["predicted_category"],
        ai_suggested_priority=ai_prediction["predicted_priority"],
        ai_confidence=max(ai_prediction["category_confidence"], ai_prediction["priority_confidence"]),
    )
    db.session.add(complaint)
    db.session.commit()

    notify_role("warden", "New Complaint Raised", f"{student.user.name} raised a complaint: {complaint.title}", "warning")
    db.session.commit()

    return jsonify({"success": True, "message": "Complaint submitted successfully.", "complaint": complaint.to_dict()}), 201


@complaints_bp.route("/my", methods=["GET"])
@student_required
def my_complaints():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    query = Complaint.query.filter_by(student_id=student.id)
    query = apply_filters(query, Complaint, ["status"])
    complaints = query.order_by(Complaint.created_at.desc()).all()
    return jsonify({"success": True, "complaints": [c.to_dict() for c in complaints]}), 200


@complaints_bp.route("/<int:complaint_id>/assign", methods=["PUT"])
@admin_or_warden_required
def assign_complaint(complaint_id):
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"success": False, "message": "Complaint not found."}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["assigned_to"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    complaint.assigned_to = data["assigned_to"]
    if complaint.status == ComplaintStatusEnum.OPEN:
        complaint.status = ComplaintStatusEnum.IN_PROGRESS
    db.session.commit()

    return jsonify({"success": True, "message": "Complaint assigned.", "complaint": complaint.to_dict()}), 200


@complaints_bp.route("/<int:complaint_id>/status", methods=["PUT"])
@admin_or_warden_required
def update_complaint_status(complaint_id):
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"success": False, "message": "Complaint not found."}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["status"])
    errors += validate_choice(data.get("status"), STATUSES, "status")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    complaint.status = data["status"]
    complaint.resolution_note = data.get("resolution_note", complaint.resolution_note)
    if data["status"] in (ComplaintStatusEnum.RESOLVED.value, ComplaintStatusEnum.REJECTED.value):
        complaint.resolved_at = datetime.utcnow()

    db.session.commit()

    notify_user(complaint.student.user_id, "Complaint Update",
                f"Your complaint '{complaint.title}' is now marked as {complaint.status.value}.", "info")
    db.session.commit()

    return jsonify({"success": True, "message": "Complaint status updated.", "complaint": complaint.to_dict()}), 200
