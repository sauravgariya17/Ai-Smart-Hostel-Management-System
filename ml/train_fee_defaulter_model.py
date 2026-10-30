"""
ml/train_fee_defaulter_model.py
------------------------------------
Trains a RandomForestClassifier on the SYNTHETIC fee-payment-behavior
dataset (ml/datasets/fee_defaulters_synthetic.csv) to estimate a
student's risk of becoming a fee defaulter.

This is explicitly a DECISION-SUPPORT tool: the service layer and API
response both carry a disclaimer that this is a risk estimate, not a
final decision, and staff must use their own judgement.

Features: total_invoices, total_due, total_paid, percent_paid,
max_days_overdue, overdue_invoice_count, avg_days_to_pay
Label: is_defaulter (0/1)

Run:
    python ml/train_fee_defaulter_model.py
"""

import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "datasets", "fee_defaulters_synthetic.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLUMNS = [
    "total_invoices", "total_due", "total_paid", "percent_paid",
    "max_days_overdue", "overdue_invoice_count", "avg_days_to_pay",
]


def train():
    if not os.path.exists(DATASET_PATH):
        raise SystemExit("Dataset not found. Run 'python ml/generate_synthetic_data.py' first.")

    df = pd.read_csv(DATASET_PATH)
    X = df[FEATURE_COLUMNS]
    y = df["is_defaulter"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=6, random_state=42, class_weight="balanced"
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    print("\n=== fee defaulter risk model ===")
    print(f"Test accuracy: {accuracy:.3f}")
    print(f"ROC-AUC: {auc:.3f}")
    print(classification_report(y_test, y_pred, zero_division=0))

    model_path = os.path.join(MODELS_DIR, "fee_defaulter_model.joblib")
    joblib.dump({"model": model, "feature_columns": FEATURE_COLUMNS}, model_path)
    print(f"Saved -> {model_path}")


if __name__ == "__main__":
    train()
