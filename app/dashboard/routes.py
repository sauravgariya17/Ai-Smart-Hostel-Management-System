"""
app/dashboard/routes.py
---------------------------
Aggregated statistics tailored to each role's dashboard:
  - Admin dashboard   : system-wide KPIs
  - Warden dashboard   : operational KPIs (complaints, attendance, visitors)
  - Student dashboard  : personal KPIs (room, fees, complaints, attendance)
"""

from datetime import datetime

from flask import jsonify
from sqlalchemy import func

from app.dashboard import dashboard_bp
from app.extensions import db
from app.models import (
    Student,
    Warden,
    Room,
    RoomAllocation,
    AllocationStatusEnum,
    StudentFee,
    Complaint,
    ComplaintStatusEnum,
    Visitor,
    Attendance,
    AttendanceStatusEnum,
    MaintenanceRequest,
    MaintenanceStatusEnum,
)
from app.utils.decorators import admin_required, admin_or_warden_required, student_required, get_current_user_id
from app.rooms.services import get_active_allocation


@dashboard_bp.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard_stats():
    """Return system-wide KPIs.

    Each KPI is intentionally queried independently.  This keeps the
    dashboard usable even when an optional/older database does not yet
    contain one of the newer module tables.
    """
    def safe_count(query_factory, default=0):
        try:
            value = query_factory()
            return int(value or 0)
        except Exception:
            db.session.rollback()
            return default

    def safe_scalar(query_factory, default=0):
        try:
            value = query_factory()
            return value if value is not None else default
        except Exception:
            db.session.rollback()
            return default

    total_students = safe_count(lambda: Student.query.count())
    total_wardens = safe_count(lambda: Warden.query.count())
    total_rooms = safe_count(lambda: Room.query.count())

    total_capacity = safe_scalar(
        lambda: db.session.query(func.coalesce(func.sum(Room.capacity), 0)).scalar()
    )
    total_occupied = safe_scalar(
        lambda: db.session.query(func.coalesce(func.sum(Room.occupied_beds), 0)).scalar()
    )

    open_complaints = safe_count(
        lambda: Complaint.query.filter(
            Complaint.status.in_([ComplaintStatusEnum.OPEN, ComplaintStatusEnum.IN_PROGRESS])
        ).count()
    )

    pending_maintenance = safe_count(
        lambda: MaintenanceRequest.query.filter_by(status=MaintenanceStatusEnum.PENDING).count()
    )

    total_due = safe_scalar(
        lambda: db.session.query(func.coalesce(func.sum(StudentFee.amount_due), 0)).scalar()
    )
    total_paid = safe_scalar(
        lambda: db.session.query(func.coalesce(func.sum(StudentFee.amount_paid), 0)).scalar()
    )

    today = datetime.utcnow().date()
    visitors_today = safe_count(
        lambda: Visitor.query.filter(func.date(Visitor.check_in_time) == today).count()
    )

    total_capacity = int(total_capacity or 0)
    total_occupied = int(total_occupied or 0)
    total_due = float(total_due or 0)
    total_paid = float(total_paid or 0)

    return jsonify({
        "success": True,
        "stats": {
            "total_students": total_students,
            "total_wardens": total_wardens,
            "total_rooms": total_rooms,
            "rooms_occupied": total_occupied,
            "rooms_available": max(total_capacity - total_occupied, 0),
            "occupancy_rate_percent": round((total_occupied / total_capacity) * 100, 1) if total_capacity else 0,
            "open_complaints": open_complaints,
            "pending_maintenance": pending_maintenance,
            "total_fee_due": total_due,
            "total_fee_collected": total_paid,
            "total_fee_outstanding": total_due - total_paid,
            "visitors_today": visitors_today,
        },
    }), 200


@dashboard_bp.route("/warden", methods=["GET"])
@admin_or_warden_required
def warden_dashboard_stats():
    open_complaints = Complaint.query.filter(
        Complaint.status.in_([ComplaintStatusEnum.OPEN, ComplaintStatusEnum.IN_PROGRESS])
    ).count()

    today = datetime.utcnow().date()
    present_today = Attendance.query.filter(
        Attendance.attendance_date == today, Attendance.status == AttendanceStatusEnum.PRESENT
    ).count()
    total_students = Student.query.count()

    active_visitors = Visitor.query.filter(Visitor.check_out_time.is_(None)).count()
    pending_maintenance = MaintenanceRequest.query.filter_by(status=MaintenanceStatusEnum.PENDING).count()

    return jsonify({
        "success": True,
        "stats": {
            "open_complaints": open_complaints,
            "present_today": present_today,
            "total_students": total_students,
            "attendance_rate_percent": round((present_today / total_students) * 100, 1) if total_students else 0,
            "active_visitors": active_visitors,
            "pending_maintenance": pending_maintenance,
        },
    }), 200


@dashboard_bp.route("/student", methods=["GET"])
@student_required
def student_dashboard_stats():
    student = Student.query.filter_by(user_id=get_current_user_id()).first()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    allocation = get_active_allocation(student.id)

    pending_fees = StudentFee.query.filter(StudentFee.student_id == student.id, StudentFee.status != "paid").all()
    total_due = sum(fee.balance for fee in pending_fees)

    open_complaints = Complaint.query.filter(
        Complaint.student_id == student.id, Complaint.status.in_(["open", "in_progress"])
    ).count()

    total_attendance_days = Attendance.query.filter_by(student_id=student.id).count()
    present_days = Attendance.query.filter_by(student_id=student.id, status=AttendanceStatusEnum.PRESENT).count()

    return jsonify({
        "success": True,
        "stats": {
            "room_number": allocation.room.room_number if allocation else None,
            "hostel_name": allocation.room.hostel.name if allocation else None,
            "total_fee_due": total_due,
            "open_complaints": open_complaints,
            "attendance_rate_percent": round((present_days / total_attendance_days) * 100, 1) if total_attendance_days else 0,
        },
    }), 200
