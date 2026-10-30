"""
app/ai/services/model_loader.py
-----------------------------------
Small shared utility used by every AI service module to load a trained
`.joblib` artifact from the ML_MODELS_DIR configured in config.py.

Models are cached in-process after the first load (training scripts are
run offline via `python ml/train_*.py`; the Flask app only ever reads
the resulting artifacts). If an artifact is missing — e.g. someone runs
the app before running the training scripts — `load_model` returns
`None` instead of raising, so every AI service can fail gracefully with
a clear message instead of crashing the whole request.
"""

import os
import logging

import joblib
from flask import current_app

logger = logging.getLogger(__name__)

_MODEL_CACHE: dict = {}


def load_model(filename: str):
    """Load (and cache) a joblib artifact from the configured ML models
    directory. Returns None if the file doesn't exist or fails to load."""
    if filename in _MODEL_CACHE:
        return _MODEL_CACHE[filename]

    models_dir = current_app.config.get("ML_MODELS_DIR")
    path = os.path.join(models_dir, filename)

    if not os.path.exists(path):
        logger.warning(
            "AI model artifact not found: %s. Run the corresponding "
            "training script in ml/ to generate it.", path
        )
        return None

    try:
        model = joblib.load(path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load AI model artifact %s: %s", path, exc)
        return None

    _MODEL_CACHE[filename] = model
    return model


def clear_model_cache() -> None:
    """Used by tests / after retraining to force a fresh load."""
    _MODEL_CACHE.clear()
