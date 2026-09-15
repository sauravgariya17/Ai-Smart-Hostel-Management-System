"""
app/maintenance/routes.py
-----------------------------
Maintenance Management: wardens/admins raise and track work orders for
room/facility repairs.
"""

from datetime import datetime

from flask import request, jsonify

from app.maintenance import maintenance_bp
from app.extensions import db
from app.models import MaintenanceRequest, MaintenancePriorityEnum, MaintenanceStatusEnum, Room
from app.utils.decorators import admin_or_warden_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_filters, apply_sort
from app.utils.validators import validate_required_fields, validate_choice

PRIORITIES = [e.value for e in MaintenancePriorityEnum]
STATUSES = [e.value for e in MaintenanceStatusEnum]


@maintenance_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_maintenance_requests():
    query = MaintenanceRequest.query
    query = apply_search(query, MaintenanceRequest, ["category"])
    query = apply_filters(query, MaintenanceRequest, ["status", "priority", "room_id", "assigned_to"])
    query = apply_sort(query, MaintenanceRequest, ["id", "created_at", "priority"], default_field="created_at")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@maintenance_bp.route("/<int:request_id>", methods=["GET"])
@admin_or_warden_required
def get_maintenance_request(request_id):
    record = MaintenanceRequest.query.get(request_id)
    if not record:
        return jsonify({"success": False, "message": "Maintenance request not found."}), 404
    return jsonify({"success": True, "maintenance_request": record.to_dict()}), 200


@maintenance_bp.route("", methods=["POST"])
@admin_or_warden_required
def create_maintenance_request():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["category"])
    if "priority" in data:
        errors += validate_choice(data.get("priority"), PRIORITIES, "priority")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if data.get("room_id") and not Room.query.get(data["room_id"]):
        return jsonify({"success": False, "message": "Invalid room_id."}), 404

    record = MaintenanceRequest(
        room_id=data.get("room_id"),
        reported_by=get_current_user_id(),
        category=data["category"].strip(),
        description=data.get("description"),
        priority=data.get("priority", MaintenancePriorityEnum.MEDIUM.value),
        assigned_to=data.get("assigned_to"),
        status=MaintenanceStatusEnum.PENDING,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"success": True, "message": "Maintenance request created.", "maintenance_request": record.to_dict()}), 201


@maintenance_bp.route("/<int:request_id>", methods=["PUT"])
@admin_or_warden_required
def update_maintenance_request(request_id):
    record = MaintenanceRequest.query.get(request_id)
    if not record:
        return jsonify({"success": False, "message": "Maintenance request not found."}), 404

    data = request.get_json(silent=True) or {}

    if "status" in data:
        errors = validate_choice(data["status"], STATUSES, "status")
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
        record.status = data["status"]
        if data["status"] == MaintenanceStatusEnum.COMPLETED.value:
            record.completed_at = datetime.utcnow()

    if "priority" in data:
        errors = validate_choice(data["priority"], PRIORITIES, "priority")
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
        record.priority = data["priority"]

    for field in ["assigned_to", "description", "cost"]:
        if field in data:
            setattr(record, field, data[field])

    db.session.commit()
    return jsonify({"success": True, "message": "Maintenance request updated.", "maintenance_request": record.to_dict()}), 200


@maintenance_bp.route("/<int:request_id>", methods=["DELETE"])
@admin_or_warden_required
def delete_maintenance_request(request_id):
    record = MaintenanceRequest.query.get(request_id)
    if not record:
        return jsonify({"success": False, "message": "Maintenance request not found."}), 404

    db.session.delete(record)
    db.session.commit()
    return jsonify({"success": True, "message": "Maintenance request deleted."}), 200
