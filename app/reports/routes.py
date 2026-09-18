"""
app/reports/routes.py
-------------------------
Read-only aggregate analytics used by the Reports page and by chart
widgets on the dashboards. All admin/warden restricted.
"""

from datetime import datetime, timedelta

from flask import jsonify
from sqlalchemy import func

from app.reports import reports_bp
from app.extensions import db
from app.models import (
    Room,
    RoomStatusEnum,
    Hostel,
    StudentFee,
    Payment,
    FeeStatusEnum,
    Complaint,
    ComplaintStatusEnum,
    ComplaintCategoryEnum,
    Attendance,
    AttendanceStatusEnum,
    Student,
    MaintenanceRequest,
    MaintenanceStatusEnum,
)
from app.utils.decorators import admin_or_warden_required


@reports_bp.route("/occupancy", methods=["GET"])
@admin_or_warden_required
def occupancy_report():
    total_rooms = Room.query.count()
    total_capacity = db.session.query(func.coalesce(func.sum(Room.capacity), 0)).scalar()
    total_occupied = db.session.query(func.coalesce(func.sum(Room.occupied_beds), 0)).scalar()

    by_status = dict(
        db.session.query(Room.status, func.count(Room.id)).group_by(Room.status).all()
    )
    by_status = {status.value if hasattr(status, "value") else status: count for status, count in by_status.items()}

    by_hostel = (
        db.session.query(Hostel.name, func.coalesce(func.sum(Room.capacity), 0), func.coalesce(func.sum(Room.occupied_beds), 0))
        .outerjoin(Room, Room.hostel_id == Hostel.id)
        .group_by(Hostel.id)
        .all()
    )

    occupancy_rate = round((total_occupied / total_capacity) * 100, 1) if total_capacity else 0

    return jsonify({
        "success": True,
        "report": {
            "total_rooms": total_rooms,
            "total_capacity": int(total_capacity),
            "total_occupied": int(total_occupied),
            "occupancy_rate_percent": occupancy_rate,
            "rooms_by_status": by_status,
            "by_hostel": [
                {"hostel_name": name, "capacity": int(cap), "occupied": int(occ)}
                for name, cap, occ in by_hostel
            ],
        },
    }), 200


@reports_bp.route("/fee-collection", methods=["GET"])
@admin_or_warden_required
def fee_collection_report():
    total_due = db.session.query(func.coalesce(func.sum(StudentFee.amount_due), 0)).scalar()
    total_paid = db.session.query(func.coalesce(func.sum(StudentFee.amount_paid), 0)).scalar()

    by_status = dict(
        db.session.query(StudentFee.status, func.count(StudentFee.id)).group_by(StudentFee.status).all()
    )
    by_status = {status.value if hasattr(status, "value") else status: count for status, count in by_status.items()}

    # Grouped in Python (rather than a vendor-specific SQL date-format
    # function) so this query behaves identically across MySQL/SQLite.
    last_6_months_cutoff = datetime.utcnow() - timedelta(days=180)
    recent_payments = Payment.query.filter(Payment.payment_date >= last_6_months_cutoff).all()

    monthly_totals: dict[str, float] = {}
    for payment in recent_payments:
        month_key = payment.payment_date.strftime("%Y-%m")
        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + float(payment.amount)

    monthly_collection = [{"month": month, "amount": amount} for month, amount in sorted(monthly_totals.items())]

    return jsonify({
        "success": True,
        "report": {
            "total_due": float(total_due),
            "total_collected": float(total_paid),
            "total_outstanding": float(total_due) - float(total_paid),
            "invoices_by_status": by_status,
            "monthly_collection": monthly_collection,
        },
    }), 200


@reports_bp.route("/complaints", methods=["GET"])
@admin_or_warden_required
def complaints_report():
    by_status = dict(db.session.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all())
    by_status = {s.value if hasattr(s, "value") else s: c for s, c in by_status.items()}

    by_category = dict(db.session.query(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category).all())
    by_category = {c.value if hasattr(c, "value") else c: n for c, n in by_category.items()}

    total = Complaint.query.count()
    resolved = Complaint.query.filter_by(status=ComplaintStatusEnum.RESOLVED).count()
    resolution_rate = round((resolved / total) * 100, 1) if total else 0

    return jsonify({
        "success": True,
        "report": {
            "total_complaints": total,
            "resolution_rate_percent": resolution_rate,
            "by_status": by_status,
            "by_category": by_category,
        },
    }), 200


@reports_bp.route("/attendance", methods=["GET"])
@admin_or_warden_required
def attendance_report():
    today = datetime.utcnow().date()
    total_students = Student.query.count()

    today_counts = dict(
        db.session.query(Attendance.status, func.count(Attendance.id))
        .filter(Attendance.attendance_date == today)
        .group_by(Attendance.status)
        .all()
    )
    today_counts = {s.value if hasattr(s, "value") else s: c for s, c in today_counts.items()}

    present_today = today_counts.get(AttendanceStatusEnum.PRESENT.value, 0)
    attendance_rate = round((present_today / total_students) * 100, 1) if total_students else 0

    return jsonify({
        "success": True,
        "report": {
            "total_students": total_students,
            "today_attendance_rate_percent": attendance_rate,
            "today_breakdown": today_counts,
        },
    }), 200


@reports_bp.route("/maintenance", methods=["GET"])
@admin_or_warden_required
def maintenance_report():
    by_status = dict(
        db.session.query(MaintenanceRequest.status, func.count(MaintenanceRequest.id))
        .group_by(MaintenanceRequest.status)
        .all()
    )
    by_status = {s.value if hasattr(s, "value") else s: c for s, c in by_status.items()}

    total_cost = db.session.query(func.coalesce(func.sum(MaintenanceRequest.cost), 0)).scalar()
    pending = MaintenanceRequest.query.filter_by(status=MaintenanceStatusEnum.PENDING).count()

    return jsonify({
        "success": True,
        "report": {
            "by_status": by_status,
            "pending_requests": pending,
            "total_cost_incurred": float(total_cost),
        },
    }), 200
