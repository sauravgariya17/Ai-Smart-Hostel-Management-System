"""
app/notifications/routes.py
--------------------------------
Notification System: every authenticated user can fetch notifications
addressed to them personally OR broadcast to their role; admins can
push new broadcasts.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.notifications import notifications_bp
from app.extensions import db
from app.models import Notification
from app.utils.decorators import admin_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.validators import validate_required_fields, validate_choice
from app.utils.notify import notify_role, notify_user
from sqlalchemy import or_, and_


def _visible_notifications_query():
    user_id = get_current_user_id()
    role = get_jwt().get("role")
    return Notification.query.filter(
        or_(Notification.user_id == user_id, and_(Notification.user_id.is_(None), Notification.target_role == role))
    )


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    query = _visible_notifications_query().order_by(Notification.created_at.desc())
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@notifications_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def unread_count():
    count = _visible_notifications_query().filter(Notification.is_read.is_(False)).count()
    return jsonify({"success": True, "unread_count": count}), 200


@notifications_bp.route("/<int:notification_id>/read", methods=["PUT"])
@jwt_required()
def mark_read(notification_id):
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({"success": False, "message": "Notification not found."}), 404

    notification.is_read = True
    db.session.commit()
    return jsonify({"success": True, "message": "Notification marked as read.", "notification": notification.to_dict()}), 200


@notifications_bp.route("/read-all", methods=["PUT"])
@jwt_required()
def mark_all_read():
    notifications = _visible_notifications_query().filter(Notification.is_read.is_(False)).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return jsonify({"success": True, "message": f"{len(notifications)} notification(s) marked as read."}), 200


@notifications_bp.route("/<int:notification_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notification_id):
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({"success": False, "message": "Notification not found."}), 404

    db.session.delete(notification)
    db.session.commit()
    return jsonify({"success": True, "message": "Notification deleted."}), 200


@notifications_bp.route("/broadcast", methods=["POST"])
@admin_required
def broadcast_notification():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["title", "message", "target_role"])
    errors += validate_choice(data.get("target_role"), ["admin", "warden", "student"], "target_role")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    notification = notify_role(
        role=data["target_role"],
        title=data["title"].strip(),
        message=data["message"].strip(),
        notif_type=data.get("notif_type", "info"),
    )
    db.session.commit()

    return jsonify({"success": True, "message": "Broadcast sent.", "notification": notification.to_dict()}), 201


@notifications_bp.route("/send", methods=["POST"])
@admin_required
def send_personal_notification():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["user_id", "title", "message"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    notification = notify_user(
        user_id=data["user_id"],
        title=data["title"].strip(),
        message=data["message"].strip(),
        notif_type=data.get("notif_type", "info"),
    )
    db.session.commit()

    return jsonify({"success": True, "message": "Notification sent.", "notification": notification.to_dict()}), 201
