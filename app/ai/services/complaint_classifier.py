"""
app/ai/services/complaint_classifier.py
-------------------------------------------
AI Complaint Classification + Priority Prediction.

Wraps the two TF-IDF + Logistic Regression pipelines trained by
ml/train_complaint_classifier.py. Predictions are always constrained to
the existing ComplaintCategoryEnum / ComplaintPriorityEnum values (see
app/models/complaint.py) so the result can be written straight into the
Complaint model without any extra mapping step.

If the trained models aren't available for some reason, a lightweight
keyword-matching fallback keeps the feature usable (with lower
confidence) instead of failing outright.
"""

from app.ai.services.model_loader import load_model
from app.models import ComplaintCategoryEnum, ComplaintPriorityEnum

CATEGORY_MODEL_FILE = "complaint_category_model.joblib"
PRIORITY_MODEL_FILE = "complaint_priority_model.joblib"

VALID_CATEGORIES = [e.value for e in ComplaintCategoryEnum]
VALID_PRIORITIES = [e.value for e in ComplaintPriorityEnum]

# Keyword fallback used only if the trained model artifacts are missing.
_CATEGORY_KEYWORDS = {
    "electrical": ["fan", "light", "bulb", "switch", "socket", "electric", "wiring", "short circuit", "power"],
    "plumbing": ["tap", "water", "leak", "pipe", "drain", "flush", "toilet", "bathroom", "shower"],
    "cleanliness": ["dirty", "clean", "garbage", "dust", "trash", "hygien", "smell"],
    "internet": ["wifi", "internet", "network", "router", "connection", "lan"],
    "food": ["food", "mess", "meal", "cook", "menu", "canteen"],
    "security": ["lock", "gate", "guard", "cctv", "theft", "security", "stranger", "fire extinguisher"],
}
_HIGH_PRIORITY_KEYWORDS = ["urgent", "immediately", "asap", "danger", "fire", "risk", "emergency", "flooding"]
_LOW_PRIORITY_KEYWORDS = ["minor", "small", "whenever", "no rush", "occasionally", "slight"]


def _keyword_fallback_category(text: str) -> tuple[str, float]:
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return category, 0.5
    return ComplaintCategoryEnum.OTHER.value, 0.3


def _keyword_fallback_priority(text: str) -> tuple[str, float]:
    lowered = text.lower()
    if any(kw in lowered for kw in _HIGH_PRIORITY_KEYWORDS):
        return ComplaintPriorityEnum.HIGH.value, 0.5
    if any(kw in lowered for kw in _LOW_PRIORITY_KEYWORDS):
        return ComplaintPriorityEnum.LOW.value, 0.5
    return ComplaintPriorityEnum.MEDIUM.value, 0.4


def _predict_with_pipeline(pipeline, text: str, valid_labels: list[str]) -> tuple[str, float]:
    prediction = pipeline.predict([text])[0]
    confidence = 0.6

    if hasattr(pipeline, "predict_proba"):
        try:
            probabilities = pipeline.predict_proba([text])[0]
            confidence = float(max(probabilities))
        except Exception:  # noqa: BLE001
            pass

    if prediction not in valid_labels:
        prediction = valid_labels[0]

    return prediction, round(confidence, 3)


def classify_complaint(title: str, description: str = "") -> dict:
    """
    Predict the category and priority for a complaint given its text.

    Returns:
        {
            "predicted_category": "electrical",
            "category_confidence": 0.87,
            "predicted_priority": "high",
            "priority_confidence": 0.74,
            "source": "model" | "fallback",
        }
    """
    text = f"{title or ''}. {description or ''}".strip()
    if not text:
        return {
            "predicted_category": ComplaintCategoryEnum.OTHER.value,
            "category_confidence": 0.0,
            "predicted_priority": ComplaintPriorityEnum.MEDIUM.value,
            "priority_confidence": 0.0,
            "source": "fallback",
        }

    category_model = load_model(CATEGORY_MODEL_FILE)
    priority_model = load_model(PRIORITY_MODEL_FILE)
    source = "model"

    if category_model is not None:
        predicted_category, category_confidence = _predict_with_pipeline(category_model, text, VALID_CATEGORIES)
    else:
        predicted_category, category_confidence = _keyword_fallback_category(text)
        source = "fallback"

    if priority_model is not None:
        predicted_priority, priority_confidence = _predict_with_pipeline(priority_model, text, VALID_PRIORITIES)
    else:
        predicted_priority, priority_confidence = _keyword_fallback_priority(text)
        source = "fallback"

    return {
        "predicted_category": predicted_category,
        "category_confidence": category_confidence,
        "predicted_priority": predicted_priority,
        "priority_confidence": priority_confidence,
        "source": source,
    }
