"""
app/attendance/routes.py
----------------------------
Attendance Management: wardens/admins mark daily attendance (single or
bulk per hostel/room), students can view their own history.
"""

from datetime import date, datetime
from io import BytesIO
import socket
from urllib.parse import urlsplit, urlunsplit

import qrcode
from flask import request, jsonify, current_app, send_file, url_for
from itsdangerous import URLSafeSerializer, BadSignature

from app.attendance import attendance_bp
from app.extensions import db
from app.models import Attendance, AttendanceStatusEnum, Student
from app.utils.decorators import admin_or_warden_required, student_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_filters, apply_date_range, apply_sort
from app.utils.validators import validate_required_fields, validate_choice

ATTENDANCE_STATUSES = [e.value for e in AttendanceStatusEnum]


def _current_student_or_404():
    return Student.query.filter_by(user_id=get_current_user_id()).first()


def _parse_date(value):
    if not value:
        return datetime.utcnow().date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return datetime.utcnow().date()


def _daily_qr_serializer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="daily-attendance-qr-v1")


def _today_qr_token():
    # URLSafeSerializer output is deterministic, so all staff see the same QR
    # for a given day. The date embedded in it makes yesterday's QR unusable.
    return _daily_qr_serializer().dumps({"date": date.today().isoformat()})


@attendance_bp.route("/qr", methods=["GET"])
@admin_or_warden_required
def daily_attendance_qr():
    token = _today_qr_token()
    checkin_url = url_for("main.attendance_page", _external=True, checkin=token)
    parsed_url = urlsplit(checkin_url)
    hostname = parsed_url.hostname
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"}:
        # A QR containing localhost would send a student's phone back to the
        # phone itself. Resolve the server's LAN interface for local demos.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                hostname = probe.getsockname()[0]
        except OSError:
            pass
    netloc = f"{hostname}:{parsed_url.port}" if parsed_url.port else hostname
    checkin_url = urlunsplit((parsed_url.scheme, netloc, parsed_url.path, parsed_url.query, ""))
    image = qrcode.make(checkin_url)
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    response = send_file(output, mimetype="image/png", download_name="attendance-qr.png")
    response.headers["Cache-Control"] = "no-store"
    return response


@attendance_bp.route("/qr/checkin", methods=["POST"])
@student_required
def qr_checkin():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    try:
        payload = _daily_qr_serializer().loads(token)
    except (BadSignature, TypeError):
        return jsonify({"success": False, "message": "This attendance QR code is invalid."}), 400

    today = date.today()
    if payload.get("date") != today.isoformat():
        return jsonify({"success": False, "message": "This QR code has expired. Please scan today's code."}), 400

    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    existing = Attendance.query.filter_by(student_id=student.id, attendance_date=today).first()
    if existing:
        if existing.status == AttendanceStatusEnum.PRESENT:
            return jsonify({"success": True, "message": "Your attendance is already recorded for today."}), 200
        return jsonify({"success": False, "message": "Attendance has already been recorded for you today."}), 409

    record = Attendance(
        student_id=student.id,
        attendance_date=today,
        status=AttendanceStatusEnum.PRESENT,
        remarks="QR check-in",
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"success": True, "message": "Attendance recorded for today.", "attendance": record.to_dict()}), 201


@attendance_bp.route("", methods=["GET"])
@admin_or_warden_required
def list_attendance():
    query = Attendance.query
    query = apply_filters(query, Attendance, ["student_id", "status"])
    query = apply_date_range(query, Attendance, "attendance_date")
    query = apply_sort(query, Attendance, ["id", "attendance_date"], default_field="attendance_date")
    result = paginate_query(query, default_per_page=20)
    return jsonify({"success": True, **result}), 200


@attendance_bp.route("", methods=["POST"])
@admin_or_warden_required
def mark_attendance():
    """Mark (or update) a single student's attendance for a given date."""
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["student_id", "status"])
    errors += validate_choice(data.get("status"), ATTENDANCE_STATUSES, "status")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    student = Student.query.get(data["student_id"])
    if not student:
        return jsonify({"success": False, "message": "Invalid student_id."}), 404

    attendance_date = _parse_date(data.get("attendance_date"))

    record = Attendance.query.filter_by(student_id=student.id, attendance_date=attendance_date).first()
    if record:
        record.status = data["status"]
        record.remarks = data.get("remarks")
        record.marked_by = get_current_user_id()
    else:
        record = Attendance(
            student_id=student.id,
            attendance_date=attendance_date,
            status=data["status"],
            remarks=data.get("remarks"),
            marked_by=get_current_user_id(),
        )
        db.session.add(record)

    db.session.commit()
    return jsonify({"success": True, "message": "Attendance recorded.", "attendance": record.to_dict()}), 200


@attendance_bp.route("/bulk", methods=["POST"])
@admin_or_warden_required
def bulk_mark_attendance():
    """
    Mark attendance for many students at once:
    {
        "attendance_date": "2026-08-01",
        "records": [{"student_id": 1, "status": "present"}, {"student_id": 2, "status": "absent"}]
    }
    """
    data = request.get_json(silent=True) or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"success": False, "message": "'records' must be a non-empty list."}), 400

    attendance_date = _parse_date(data.get("attendance_date"))
    saved = []
    errors = []

    for entry in records:
        student_id = entry.get("student_id")
        status = entry.get("status")

        if status not in ATTENDANCE_STATUSES:
            errors.append(f"Invalid status for student_id {student_id}.")
            continue

        existing = Attendance.query.filter_by(student_id=student_id, attendance_date=attendance_date).first()
        if existing:
            existing.status = status
            existing.remarks = entry.get("remarks")
            existing.marked_by = get_current_user_id()
            saved.append(existing)
        else:
            new_record = Attendance(
                student_id=student_id,
                attendance_date=attendance_date,
                status=status,
                remarks=entry.get("remarks"),
                marked_by=get_current_user_id(),
            )
            db.session.add(new_record)
            saved.append(new_record)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Attendance recorded for {len(saved)} student(s).",
        "errors": errors,
        "attendance": [a.to_dict() for a in saved],
    }), 200


@attendance_bp.route("/my", methods=["GET"])
@student_required
def my_attendance():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    query = Attendance.query.filter_by(student_id=student.id)
    query = apply_date_range(query, Attendance, "attendance_date")
    records = query.order_by(Attendance.attendance_date.desc()).all()
    return jsonify({"success": True, "attendance": [r.to_dict() for r in records]}), 200
