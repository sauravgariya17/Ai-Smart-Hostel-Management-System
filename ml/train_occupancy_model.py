"""
ml/train_occupancy_model.py
--------------------------------
Trains a RandomForestRegressor on the SYNTHETIC daily occupancy dataset
(ml/datasets/occupancy_synthetic.csv) to forecast future hostel-wide
occupancy percentage.

Features used: trend_index (day count since dataset start), day_of_week,
sin/cos-encoded day_of_year (captures yearly seasonality without a
discontinuity at the year boundary).

Also saves a small metadata dict (last trend_index / last date seen)
alongside the model so the prediction service knows where to continue
the trend line from when forecasting "the next N days".

Run:
    python ml/train_occupancy_model.py
"""

import os
import math
from datetime import datetime

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "datasets", "occupancy_synthetic.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["day_of_year_sin"] = df["day_of_year"].apply(lambda d: math.sin((d / 365.0) * 2 * math.pi))
    df["day_of_year_cos"] = df["day_of_year"].apply(lambda d: math.cos((d / 365.0) * 2 * math.pi))
    return df


FEATURE_COLUMNS = ["trend_index", "day_of_week", "day_of_year_sin", "day_of_year_cos"]


def train():
    if not os.path.exists(DATASET_PATH):
        raise SystemExit("Dataset not found. Run 'python ml/generate_synthetic_data.py' first.")

    df = pd.read_csv(DATASET_PATH, parse_dates=["date"])
    df = _engineer_features(df)

    X = df[FEATURE_COLUMNS]
    y = df["occupancy_percent"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("\n=== occupancy forecasting model ===")
    print(f"MAE: {mae:.2f} percentage points")
    print(f"R^2: {r2:.3f}")

    model_path = os.path.join(MODELS_DIR, "occupancy_model.joblib")
    joblib.dump(model, model_path)

    metadata = {
        "feature_columns": FEATURE_COLUMNS,
        "last_trend_index": int(df["trend_index"].max()),
        "last_date": df["date"].max().date().isoformat(),
        "trained_at": datetime.utcnow().isoformat(),
    }
    metadata_path = os.path.join(MODELS_DIR, "occupancy_model_meta.joblib")
    joblib.dump(metadata, metadata_path)

    print(f"Saved model -> {model_path}")
    print(f"Saved metadata -> {metadata_path}")


if __name__ == "__main__":
    train()
