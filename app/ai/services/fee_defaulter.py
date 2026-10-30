"""
app/ai/services/fee_defaulter.py
-------------------------------------
Fee Defaulter Prediction (decision support, NOT an automatic action).

For every student who currently has at least one fee invoice, we compute
live behavioral features straight from the existing StudentFee/Payment
models (reused as-is, no schema changes), feed them into the
RandomForestClassifier trained by ml/train_fee_defaulter_model.py, and
return a risk score + risk level.

Every response explicitly carries a disclaimer: this flags students for
staff to review, it does not take any action on its own and must not be
treated as a final determination.
"""

from datetime import date

import pandas as pd

from app.models import Student, StudentFee
from app.ai.services.model_loader import load_model

MODEL_FILE = "fee_defaulter_model.joblib"

DISCLAIMER = (
    "This is an AI-generated risk estimate based on historical payment "
    "patterns (trained on demo data) — it is a decision-support signal for "
    "staff review, not an automatic determination of default. Always verify "
    "with the student's actual records before taking action."
)


def _compute_student_features(student: Student) -> dict | None:
    invoices = list(student.fee_invoices)
    if not invoices:
        return None

    total_invoices = len(invoices)
    total_due = sum(float(i.amount_due) for i in invoices)
    total_paid = sum(float(i.amount_paid) for i in invoices)
    percent_paid = round(total_paid / total_due, 3) if total_due > 0 else 1.0

    today = date.today()
    overdue_invoices = [i for i in invoices if i.balance > 0 and i.due_date < today]
    max_days_overdue = max([(today - i.due_date).days for i in overdue_invoices], default=0)
    overdue_invoice_count = len(overdue_invoices)

    # avg_days_to_pay: for invoices that have at least one payment, average
    # gap between due_date and the invoice's most recent payment date.
    days_to_pay_samples = []
    for invoice in invoices:
        if invoice.payments:
            latest_payment = max(invoice.payments, key=lambda p: p.payment_date)
            delta = (latest_payment.payment_date.date() - invoice.due_date).days
            days_to_pay_samples.append(max(delta, 0))
    avg_days_to_pay = round(sum(days_to_pay_samples) / len(days_to_pay_samples)) if days_to_pay_samples else 0

    return {
        "total_invoices": total_invoices,
        "total_due": round(total_due, 2),
        "total_paid": round(total_paid, 2),
        "percent_paid": percent_paid,
        "max_days_overdue": max_days_overdue,
        "overdue_invoice_count": overdue_invoice_count,
        "avg_days_to_pay": avg_days_to_pay,
    }


def _risk_level(probability: float) -> str:
    if probability >= 0.66:
        return "high"
    if probability >= 0.33:
        return "medium"
    return "low"


def _rule_based_probability(features: dict) -> float:
    """Fallback scoring used only if the trained model artifact is missing."""
    score = 0.0
    if features["percent_paid"] < 0.5:
        score += 0.4
    elif features["percent_paid"] < 0.75:
        score += 0.2
    if features["max_days_overdue"] > 60:
        score += 0.35
    elif features["max_days_overdue"] > 20:
        score += 0.2
    if features["overdue_invoice_count"] >= 2:
        score += 0.25
    return min(score, 0.97)


def predict_defaulters(limit: int = None) -> dict:
    """
    Returns:
        {
            "students": [
                {
                    "student_id": 5, "student_name": "...", "roll_number": "...",
                    "features": {...}, "risk_probability": 0.82, "risk_level": "high",
                }, ...
            ],
            "source": "model" | "fallback",
            "disclaimer": "...",
        }
    """
    model_bundle = load_model(MODEL_FILE)
    source = "model" if model_bundle else "fallback"

    students = Student.query.all()
    results = []

    for student in students:
        features = _compute_student_features(student)
        if features is None:
            continue  # no fee history yet -> nothing to assess

        if model_bundle:
            model = model_bundle["model"]
            feature_columns = model_bundle["feature_columns"]
            feature_df = pd.DataFrame([[features[col] for col in feature_columns]], columns=feature_columns)
            probability = float(model.predict_proba(feature_df)[0][1])
        else:
            probability = _rule_based_probability(features)

        results.append({
            "student_id": student.id,
            "student_name": student.user.name if student.user else None,
            "roll_number": student.roll_number,
            "features": features,
            "risk_probability": round(probability, 3),
            "risk_level": _risk_level(probability),
        })

    results.sort(key=lambda r: r["risk_probability"], reverse=True)
    if limit:
        results = results[:limit]

    return {"students": results, "source": source, "disclaimer": DISCLAIMER}
