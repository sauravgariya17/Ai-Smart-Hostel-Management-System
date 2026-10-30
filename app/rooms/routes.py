"""
app/rooms/routes.py
----------------------
Endpoints for:
  Room Management     : CRUD on rooms
  Room Availability    : list rooms with free beds (used by allocation UI
                         and by students requesting a transfer)
  Room Allocation      : assign / vacate a student's room
  Room Transfer        : student-initiated transfer requests + approval
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app.rooms import rooms_bp
from app.extensions import db
from app.models import (
    Room,
    RoomAllocation,
    RoomTransferRequest,
    RoomTypeEnum,
    RoomStatusEnum,
    AllocationStatusEnum,
    TransferStatusEnum,
    Student,
)
from app.rooms.services import allocate_room, vacate_room, transfer_room, RoomAllocationError, get_active_allocation
from app.utils.decorators import admin_required, admin_or_warden_required, student_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_filters, apply_sort
from app.utils.validators import validate_required_fields, validate_choice, is_positive_amount
from app.utils.notify import notify_role

ROOM_TYPES = [e.value for e in RoomTypeEnum]


def _current_student_or_404():
    student = Student.query.filter_by(user_id=get_current_user_id()).first()
    return student


# ======================================================================
# ROOM MANAGEMENT
# ======================================================================

@rooms_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_rooms():
    query = Room.query
    query = apply_search(query, Room, ["room_number"])
    query = apply_filters(query, Room, ["hostel_id", "block_id", "room_type", "status"])
    query = apply_sort(query, Room, ["id", "room_number", "capacity", "monthly_rent"], default_field="room_number")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@rooms_bp.route("/available", methods=["GET"])
@jwt_required()
def available_rooms():
    """Room Availability: rooms with free beds, optionally filtered by
    hostel/room_type. Open to any authenticated role since students need
    this list when submitting a transfer request."""
    query = Room.query.filter(Room.status != RoomStatusEnum.MAINTENANCE, Room.occupied_beds < Room.capacity)
    query = apply_filters(query, Room, ["hostel_id", "room_type"])
    rooms = query.order_by(Room.room_number.asc()).all()
    return jsonify({"success": True, "rooms": [r.to_dict() for r in rooms]}), 200


@rooms_bp.route("/<int:room_id>", methods=["GET"])
@admin_or_warden_required
def get_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"success": False, "message": "Room not found."}), 404
    data = room.to_dict()
    data["current_occupants"] = [
        a.to_dict() for a in room.allocations if a.status == AllocationStatusEnum.ACTIVE
    ]
    return jsonify({"success": True, "room": data}), 200


@rooms_bp.route("", methods=["POST"])
@admin_or_warden_required
def create_room():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["hostel_id", "room_number", "room_type", "capacity", "monthly_rent"])
    errors += validate_choice(data.get("room_type"), ROOM_TYPES, "room_type")
    if not is_positive_amount(data.get("monthly_rent")):
        errors.append("'monthly_rent' must be a positive number.")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if Room.query.filter_by(hostel_id=data["hostel_id"], room_number=str(data["room_number"]).strip()).first():
        return jsonify({"success": False, "message": "This room number already exists in the selected hostel."}), 409

    room = Room(
        hostel_id=data["hostel_id"],
        block_id=data.get("block_id"),
        room_number=str(data["room_number"]).strip(),
        floor=data.get("floor", 1),
        room_type=data["room_type"],
        capacity=int(data["capacity"]),
        monthly_rent=data["monthly_rent"],
        status=RoomStatusEnum.AVAILABLE,
    )
    db.session.add(room)
    db.session.commit()

    return jsonify({"success": True, "message": "Room created successfully.", "room": room.to_dict()}), 201


@rooms_bp.route("/<int:room_id>", methods=["PUT"])
@admin_required
def update_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"success": False, "message": "Room not found."}), 404

    data = request.get_json(silent=True) or {}

    if "room_type" in data:
        errors = validate_choice(data["room_type"], ROOM_TYPES, "room_type")
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
        room.room_type = data["room_type"]

    if "status" in data:
        errors = validate_choice(data["status"], [e.value for e in RoomStatusEnum], "status")
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
        room.status = data["status"]

    for field in ["block_id", "floor", "capacity", "monthly_rent"]:
        if field in data:
            setattr(room, field, data[field])

    room.refresh_status()
    db.session.commit()
    return jsonify({"success": True, "message": "Room updated successfully.", "room": room.to_dict()}), 200


@rooms_bp.route("/<int:room_id>", methods=["DELETE"])
@admin_required
def delete_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"success": False, "message": "Room not found."}), 404

    if room.occupied_beds > 0:
        return jsonify({"success": False, "message": "Cannot delete a room with active occupants."}), 409

    db.session.delete(room)
    db.session.commit()
    return jsonify({"success": True, "message": "Room deleted successfully."}), 200


# ======================================================================
# ROOM ALLOCATION
# ======================================================================

@rooms_bp.route("/allocations", methods=["GET"])
@admin_or_warden_required
def list_allocations():
    query = RoomAllocation.query
    query = apply_filters(query, RoomAllocation, ["status", "student_id", "room_id"])
    query = apply_sort(query, RoomAllocation, ["id", "allocated_date"], default_field="id")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@rooms_bp.route("/allocations", methods=["POST"])
@admin_or_warden_required
def create_allocation():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["student_id", "room_id"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    student = Student.query.get(data["student_id"])
    room = Room.query.get(data["room_id"])
    if not student or not room:
        return jsonify({"success": False, "message": "Invalid student_id or room_id."}), 404

    try:
        allocation = allocate_room(student, room, get_current_user_id(), remarks=data.get("remarks"))
        db.session.commit()
    except RoomAllocationError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 409

    return jsonify({"success": True, "message": "Room allocated successfully.", "allocation": allocation.to_dict()}), 201


@rooms_bp.route("/allocations/<int:allocation_id>/vacate", methods=["PUT"])
@admin_or_warden_required
def vacate_allocation(allocation_id):
    allocation = RoomAllocation.query.get(allocation_id)
    if not allocation:
        return jsonify({"success": False, "message": "Allocation not found."}), 404

    data = request.get_json(silent=True) or {}

    try:
        vacate_room(allocation, remarks=data.get("remarks"))
        db.session.commit()
    except RoomAllocationError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 409

    return jsonify({"success": True, "message": "Room vacated successfully.", "allocation": allocation.to_dict()}), 200


@rooms_bp.route("/allocations/student/<int:student_id>", methods=["GET"])
@jwt_required()
def student_allocation_history(student_id):
    allocations = (
        RoomAllocation.query.filter_by(student_id=student_id)
        .order_by(RoomAllocation.allocated_date.desc())
        .all()
    )
    return jsonify({"success": True, "allocations": [a.to_dict() for a in allocations]}), 200


@rooms_bp.route("/allocations/my", methods=["GET"])
@student_required
def my_allocation():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    active = get_active_allocation(student.id)
    return jsonify({"success": True, "allocation": active.to_dict() if active else None}), 200


# ======================================================================
# ROOM TRANSFER
# ======================================================================

@rooms_bp.route("/transfers", methods=["GET"])
@admin_or_warden_required
def list_transfer_requests():
    query = RoomTransferRequest.query
    query = apply_filters(query, RoomTransferRequest, ["status", "student_id"])
    query = apply_sort(query, RoomTransferRequest, ["id", "requested_at"], default_field="id")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@rooms_bp.route("/transfers", methods=["POST"])
@student_required
def request_transfer():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["requested_room_id"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    requested_room = Room.query.get(data["requested_room_id"])
    if not requested_room:
        return jsonify({"success": False, "message": "Invalid requested_room_id."}), 404

    current_allocation = get_active_allocation(student.id)

    transfer_request = RoomTransferRequest(
        student_id=student.id,
        current_room_id=current_allocation.room_id if current_allocation else None,
        requested_room_id=requested_room.id,
        reason=data.get("reason"),
        status=TransferStatusEnum.PENDING,
    )
    db.session.add(transfer_request)
    db.session.commit()

    notify_role("admin", "New Room Transfer Request",
                f"{student.user.name} requested a transfer to room {requested_room.room_number}.", "info")
    db.session.commit()

    return jsonify({"success": True, "message": "Transfer request submitted.", "transfer_request": transfer_request.to_dict()}), 201


@rooms_bp.route("/transfers/my", methods=["GET"])
@student_required
def my_transfer_requests():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    requests_ = (
        RoomTransferRequest.query.filter_by(student_id=student.id)
        .order_by(RoomTransferRequest.requested_at.desc())
        .all()
    )
    return jsonify({"success": True, "transfer_requests": [r.to_dict() for r in requests_]}), 200


@rooms_bp.route("/transfers/<int:request_id>/approve", methods=["PUT"])
@admin_or_warden_required
def approve_transfer(request_id):
    transfer_request = RoomTransferRequest.query.get(request_id)
    if not transfer_request:
        return jsonify({"success": False, "message": "Transfer request not found."}), 404
    if transfer_request.status != TransferStatusEnum.PENDING:
        return jsonify({"success": False, "message": "This request has already been processed."}), 409

    current_allocation = get_active_allocation(transfer_request.student_id)

    from datetime import datetime as _dt

    try:
        # A request from a student with no room is an initial allocation
        # request (for example, a room selected from the AI recommender).
        # In that case there is nothing to vacate first.
        if current_allocation:
            transfer_room(
                current_allocation,
                transfer_request.requested_room,
                get_current_user_id(),
                remarks=transfer_request.reason,
            )
        else:
            allocate_room(
                transfer_request.student,
                transfer_request.requested_room,
                get_current_user_id(),
                remarks=transfer_request.reason or "Initial room allocation approved.",
            )

        transfer_request.status = TransferStatusEnum.APPROVED
        transfer_request.processed_by = get_current_user_id()
        transfer_request.processed_at = _dt.utcnow()
        db.session.commit()
    except RoomAllocationError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 409

    return jsonify({"success": True, "message": "Transfer approved and room reassigned.", "transfer_request": transfer_request.to_dict()}), 200


@rooms_bp.route("/transfers/<int:request_id>/reject", methods=["PUT"])
@admin_or_warden_required
def reject_transfer(request_id):
    from datetime import datetime as _dt

    transfer_request = RoomTransferRequest.query.get(request_id)
    if not transfer_request:
        return jsonify({"success": False, "message": "Transfer request not found."}), 404
    if transfer_request.status != TransferStatusEnum.PENDING:
        return jsonify({"success": False, "message": "This request has already been processed."}), 409

    data = request.get_json(silent=True) or {}

    transfer_request.status = TransferStatusEnum.REJECTED
    transfer_request.remarks = data.get("remarks")
    transfer_request.processed_by = get_current_user_id()
    transfer_request.processed_at = _dt.utcnow()
    db.session.commit()

    return jsonify({"success": True, "message": "Transfer request rejected.", "transfer_request": transfer_request.to_dict()}), 200
