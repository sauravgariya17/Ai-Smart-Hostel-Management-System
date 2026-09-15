"""
app/hostels/routes.py
------------------------
CRUD for Hostel Management: Hostels (buildings) and Blocks (wings
within a hostel). Only admins can create/update/delete; any
authenticated staff can read.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app.hostels import hostels_bp
from app.extensions import db
from app.models import Hostel, Block, HostelTypeEnum, User, RoleEnum
from app.utils.decorators import admin_required, admin_or_warden_required
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_search, apply_filters
from app.utils.validators import validate_required_fields, validate_choice


HOSTEL_TYPES = [e.value for e in HostelTypeEnum]


@hostels_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_hostels():
    query = Hostel.query
    query = apply_search(query, Hostel, ["name", "address"])
    query = apply_filters(query, Hostel, ["hostel_type", "is_active"])
    result = paginate_query(query.order_by(Hostel.name.asc()), default_per_page=20)
    return jsonify({"success": True, **result}), 200


@hostels_bp.route("/all", methods=["GET"])
@jwt_required()
def list_all_hostels_lite():
    """Lightweight, unpaginated list for populating dropdowns/selects."""
    hostels = Hostel.query.filter_by(is_active=True).order_by(Hostel.name.asc()).all()
    return jsonify({"success": True, "hostels": [h.to_dict() for h in hostels]}), 200


@hostels_bp.route("/<int:hostel_id>", methods=["GET"])
@admin_or_warden_required
def get_hostel(hostel_id):
    hostel = Hostel.query.get(hostel_id)
    if not hostel:
        return jsonify({"success": False, "message": "Hostel not found."}), 404
    data = hostel.to_dict()
    data["blocks"] = [b.to_dict() for b in hostel.blocks]
    return jsonify({"success": True, "hostel": data}), 200


@hostels_bp.route("", methods=["POST"])
@admin_required
def create_hostel():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["name", "hostel_type"])
    errors += validate_choice(data.get("hostel_type"), HOSTEL_TYPES, "hostel_type")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if Hostel.query.filter_by(name=data["name"].strip()).first():
        return jsonify({"success": False, "message": "A hostel with this name already exists."}), 409

    warden_id = data.get("warden_id")
    if warden_id:
        warden_user = User.query.filter_by(id=warden_id, role=RoleEnum.WARDEN).first()
        if not warden_user:
            return jsonify({"success": False, "message": "Invalid warden_id."}), 400

    hostel = Hostel(
        name=data["name"].strip(),
        hostel_type=data["hostel_type"],
        address=data.get("address"),
        total_floors=data.get("total_floors", 1),
        warden_id=warden_id,
    )
    db.session.add(hostel)
    db.session.commit()

    return jsonify({"success": True, "message": "Hostel created successfully.", "hostel": hostel.to_dict()}), 201


@hostels_bp.route("/<int:hostel_id>", methods=["PUT"])
@admin_required
def update_hostel(hostel_id):
    hostel = Hostel.query.get(hostel_id)
    if not hostel:
        return jsonify({"success": False, "message": "Hostel not found."}), 404

    data = request.get_json(silent=True) or {}

    if "hostel_type" in data:
        errors = validate_choice(data["hostel_type"], HOSTEL_TYPES, "hostel_type")
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
        hostel.hostel_type = data["hostel_type"]

    for field in ["name", "address", "total_floors", "warden_id", "is_active"]:
        if field in data:
            setattr(hostel, field, data[field])

    db.session.commit()
    return jsonify({"success": True, "message": "Hostel updated successfully.", "hostel": hostel.to_dict()}), 200


@hostels_bp.route("/<int:hostel_id>", methods=["DELETE"])
@admin_required
def delete_hostel(hostel_id):
    hostel = Hostel.query.get(hostel_id)
    if not hostel:
        return jsonify({"success": False, "message": "Hostel not found."}), 404

    if hostel.rooms:
        return jsonify({"success": False, "message": "Cannot delete a hostel that still has rooms. Remove its rooms first."}), 409

    db.session.delete(hostel)
    db.session.commit()
    return jsonify({"success": True, "message": "Hostel deleted successfully."}), 200


# ---------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------

@hostels_bp.route("/<int:hostel_id>/blocks", methods=["GET"])
@admin_or_warden_required
def list_blocks(hostel_id):
    blocks = Block.query.filter_by(hostel_id=hostel_id).order_by(Block.name.asc()).all()
    return jsonify({"success": True, "blocks": [b.to_dict() for b in blocks]}), 200


@hostels_bp.route("/<int:hostel_id>/blocks", methods=["POST"])
@admin_required
def create_block(hostel_id):
    hostel = Hostel.query.get(hostel_id)
    if not hostel:
        return jsonify({"success": False, "message": "Hostel not found."}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["name"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if Block.query.filter_by(hostel_id=hostel_id, name=data["name"].strip()).first():
        return jsonify({"success": False, "message": "A block with this name already exists in this hostel."}), 409

    block = Block(hostel_id=hostel_id, name=data["name"].strip(), total_floors=data.get("total_floors", 1))
    db.session.add(block)
    db.session.commit()

    return jsonify({"success": True, "message": "Block created successfully.", "block": block.to_dict()}), 201


@hostels_bp.route("/blocks/<int:block_id>", methods=["DELETE"])
@admin_required
def delete_block(block_id):
    block = Block.query.get(block_id)
    if not block:
        return jsonify({"success": False, "message": "Block not found."}), 404

    db.session.delete(block)
    db.session.commit()
    return jsonify({"success": True, "message": "Block deleted successfully."}), 200
