"""
ml/train_complaint_classifier.py
------------------------------------
Trains two TF-IDF + Logistic Regression text classifiers on the
SYNTHETIC complaint dataset (ml/datasets/complaints_synthetic.csv):

  1. category_model  : predicts one of the Complaint model's existing
                        ComplaintCategoryEnum values (electrical, plumbing,
                        cleanliness, internet, food, security, other)
  2. priority_model   : predicts one of ComplaintPriorityEnum values
                        (low, medium, high)

Both are saved as scikit-learn Pipelines (vectorizer + classifier bundled
together) so the service layer can call `.predict()` / `.predict_proba()`
directly on raw text with no separate preprocessing step required.

Run:
    python ml/train_complaint_classifier.py
"""

import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "datasets", "complaints_synthetic.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=2)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


def train_and_save(target_column: str, output_filename: str):
    df = pd.read_csv(DATASET_PATH)
    X = df["text"]
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n=== {target_column} model ===")
    print(f"Test accuracy: {accuracy:.3f}")
    print(classification_report(y_test, y_pred, zero_division=0))

    output_path = os.path.join(MODELS_DIR, output_filename)
    joblib.dump(pipeline, output_path)
    print(f"Saved -> {output_path}")

    return accuracy


if __name__ == "__main__":
    if not os.path.exists(DATASET_PATH):
        raise SystemExit(
            "Dataset not found. Run 'python ml/generate_synthetic_data.py' first."
        )

    train_and_save("category", "complaint_category_model.joblib")
    train_and_save("priority", "complaint_priority_model.joblib")
