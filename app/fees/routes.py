"""
app/fees/routes.py
---------------------
Fee Management     : fee structures (master rates) + student invoices
Payment History     : payments recorded against an invoice
"""

from datetime import datetime

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app.fees import fees_bp
from app.extensions import db
from app.models import FeeStructure, StudentFee, Payment, PaymentModeEnum, Student
from app.utils.decorators import admin_required, admin_or_warden_required, student_required, get_current_user_id
from app.utils.pagination import paginate_query
from app.utils.query_helpers import apply_filters, apply_sort, apply_date_range
from app.utils.validators import validate_required_fields, validate_choice, is_positive_amount, is_valid_date
from app.utils.notify import notify_user

PAYMENT_MODES = [e.value for e in PaymentModeEnum]


def _current_student_or_404():
    return Student.query.filter_by(user_id=get_current_user_id()).first()


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ======================================================================
# FEE STRUCTURES
# ======================================================================

@fees_bp.route("/structures", methods=["GET"])
@admin_or_warden_required
def list_fee_structures():
    query = FeeStructure.query
    query = apply_filters(query, FeeStructure, ["hostel_id", "academic_year", "room_type"])
    result = paginate_query(query.order_by(FeeStructure.id.desc()), default_per_page=20)
    return jsonify({"success": True, **result}), 200


@fees_bp.route("/structures", methods=["POST"])
@admin_required
def create_fee_structure():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["academic_year", "amount"])
    if not is_positive_amount(data.get("amount")):
        errors.append("'amount' must be a positive number.")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    structure = FeeStructure(
        hostel_id=data.get("hostel_id"),
        room_type=data.get("room_type"),
        academic_year=data["academic_year"].strip(),
        amount=data["amount"],
        description=data.get("description"),
    )
    db.session.add(structure)
    db.session.commit()

    return jsonify({"success": True, "message": "Fee structure created.", "fee_structure": structure.to_dict()}), 201


@fees_bp.route("/structures/<int:structure_id>", methods=["PUT"])
@admin_required
def update_fee_structure(structure_id):
    structure = FeeStructure.query.get(structure_id)
    if not structure:
        return jsonify({"success": False, "message": "Fee structure not found."}), 404

    data = request.get_json(silent=True) or {}
    for field in ["hostel_id", "room_type", "academic_year", "amount", "description"]:
        if field in data:
            setattr(structure, field, data[field])

    db.session.commit()
    return jsonify({"success": True, "message": "Fee structure updated.", "fee_structure": structure.to_dict()}), 200


@fees_bp.route("/structures/<int:structure_id>", methods=["DELETE"])
@admin_required
def delete_fee_structure(structure_id):
    structure = FeeStructure.query.get(structure_id)
    if not structure:
        return jsonify({"success": False, "message": "Fee structure not found."}), 404

    db.session.delete(structure)
    db.session.commit()
    return jsonify({"success": True, "message": "Fee structure deleted."}), 200


# ======================================================================
# STUDENT FEE INVOICES
# ======================================================================

@fees_bp.route("/invoices", methods=["GET"])
@admin_or_warden_required
def list_invoices():
    query = StudentFee.query
    query = apply_filters(query, StudentFee, ["student_id", "status", "academic_year", "billing_month"])
    query = apply_date_range(query, StudentFee, "due_date")
    query = apply_sort(query, StudentFee, ["id", "due_date", "amount_due"], default_field="due_date", default_dir="asc")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@fees_bp.route("/invoices", methods=["POST"])
@admin_required
def create_invoice():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["student_id", "amount_due", "due_date", "academic_year"])
    if not is_positive_amount(data.get("amount_due")):
        errors.append("'amount_due' must be a positive number.")
    if data.get("due_date") and not is_valid_date(data["due_date"]):
        errors.append("'due_date' must be in YYYY-MM-DD format.")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    student = Student.query.get(data["student_id"])
    if not student:
        return jsonify({"success": False, "message": "Invalid student_id."}), 404

    invoice = StudentFee(
        student_id=student.id,
        fee_structure_id=data.get("fee_structure_id"),
        academic_year=data["academic_year"].strip(),
        billing_month=data.get("billing_month"),
        amount_due=data["amount_due"],
        amount_paid=0,
        due_date=_parse_date(data["due_date"]),
    )
    invoice.refresh_status()
    db.session.add(invoice)
    db.session.commit()

    notify_user(student.user_id, "New Fee Invoice",
                f"A new fee invoice of {data['amount_due']} has been raised, due {data['due_date']}.", "info")
    db.session.commit()

    return jsonify({"success": True, "message": "Invoice created.", "invoice": invoice.to_dict()}), 201


@fees_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@jwt_required()
def get_invoice(invoice_id):
    invoice = StudentFee.query.get(invoice_id)
    if not invoice:
        return jsonify({"success": False, "message": "Invoice not found."}), 404
    data = invoice.to_dict()
    data["payments"] = [p.to_dict() for p in invoice.payments]
    return jsonify({"success": True, "invoice": data}), 200


@fees_bp.route("/invoices/my", methods=["GET"])
@student_required
def my_invoices():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    invoices = StudentFee.query.filter_by(student_id=student.id).order_by(StudentFee.due_date.desc()).all()
    return jsonify({"success": True, "invoices": [i.to_dict() for i in invoices]}), 200


# ======================================================================
# PAYMENTS / PAYMENT HISTORY
# ======================================================================

@fees_bp.route("/payments", methods=["GET"])
@admin_or_warden_required
def list_payments():
    query = Payment.query
    query = apply_filters(query, Payment, ["student_fee_id", "payment_mode"])
    query = apply_date_range(query, Payment, "payment_date")
    query = apply_sort(query, Payment, ["id", "payment_date", "amount"], default_field="payment_date")
    result = paginate_query(query, default_per_page=15)
    return jsonify({"success": True, **result}), 200


@fees_bp.route("/payments", methods=["POST"])
@admin_or_warden_required
def record_payment():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["student_fee_id", "amount", "payment_mode"])
    errors += validate_choice(data.get("payment_mode"), PAYMENT_MODES, "payment_mode")
    if not is_positive_amount(data.get("amount")):
        errors.append("'amount' must be a positive number.")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    invoice = StudentFee.query.get(data["student_fee_id"])
    if not invoice:
        return jsonify({"success": False, "message": "Invalid student_fee_id."}), 404

    amount = float(data["amount"])
    if amount > invoice.balance:
        return jsonify({"success": False, "message": f"Amount exceeds outstanding balance of {invoice.balance:.2f}."}), 400

    payment = Payment(
        student_fee_id=invoice.id,
        amount=amount,
        payment_mode=data["payment_mode"],
        transaction_reference=data.get("transaction_reference"),
        remarks=data.get("remarks"),
        received_by=get_current_user_id(),
    )
    invoice.amount_paid = float(invoice.amount_paid) + amount
    invoice.refresh_status()

    db.session.add(payment)
    db.session.commit()

    notify_user(invoice.student.user_id, "Payment Received",
                f"Your payment of {amount:.2f} was recorded. Remaining balance: {invoice.balance:.2f}.", "success")
    db.session.commit()

    return jsonify({"success": True, "message": "Payment recorded successfully.", "payment": payment.to_dict(), "invoice": invoice.to_dict()}), 201


@fees_bp.route("/payments/my", methods=["GET"])
@student_required
def my_payment_history():
    student = _current_student_or_404()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    payments = (
        Payment.query.join(StudentFee, Payment.student_fee_id == StudentFee.id)
        .filter(StudentFee.student_id == student.id)
        .order_by(Payment.payment_date.desc())
        .all()
    )
    return jsonify({"success": True, "payments": [p.to_dict() for p in payments]}), 200
