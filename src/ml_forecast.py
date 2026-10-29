"""Training and inference helpers for the taxi-demand ML forecast."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_FILE = MODEL_DIR / "demand_forecast.joblib"
METRICS_FILE = MODEL_DIR / "demand_forecast_metrics.json"
FEATURE_COLUMNS = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
    "is_weekend", "days_since_start", "borough_Bronx", "borough_Brooklyn",
    "borough_EWR", "borough_Manhattan", "borough_Queens", "borough_Staten Island",
]


def make_features(times: Iterable[datetime], boroughs: Iterable[str], origin: datetime) -> pd.DataFrame:
    """Create only decision-time calendar and location features."""
    timestamps = pd.DatetimeIndex(pd.to_datetime(list(times)))
    if timestamps.tz is not None:
        timestamps = timestamps.tz_localize(None)
    borough_series = pd.Series(list(boroughs), dtype="string")
    data = pd.DataFrame({
        "hour_sin": np.sin(2 * np.pi * timestamps.hour / 24),
        "hour_cos": np.cos(2 * np.pi * timestamps.hour / 24),
        "dow_sin": np.sin(2 * np.pi * timestamps.day_of_week / 7),
        "dow_cos": np.cos(2 * np.pi * timestamps.day_of_week / 7),
        "month_sin": np.sin(2 * np.pi * (timestamps.month - 1) / 12),
        "month_cos": np.cos(2 * np.pi * (timestamps.month - 1) / 12),
        "is_weekend": (timestamps.day_of_week >= 5).astype(int),
        "days_since_start": (timestamps - pd.Timestamp(origin)).total_seconds() / 86400,
    })
    for name in ["Bronx", "Brooklyn", "EWR", "Manhattan", "Queens", "Staten Island"]:
        data[f"borough_{name}"] = (borough_series == name).astype(int).to_numpy()
    return data[FEATURE_COLUMNS]


def train_model(training_frame: pd.DataFrame, cutoff: Optional[pd.Timestamp] = None) -> dict:
    """Train a random forest with a chronological holdout and save its artifact."""
    frame = training_frame.copy().sort_values("pickup_hour")
    frame["pickup_hour"] = pd.to_datetime(frame["pickup_hour"])
    origin = frame["pickup_hour"].min().to_pydatetime()
    cutoff = cutoff or (frame["pickup_hour"].max() - pd.Timedelta(days=30))
    train = frame[frame["pickup_hour"] < cutoff]
    test = frame[frame["pickup_hour"] >= cutoff]
    if train.empty or test.empty:
        raise ValueError("Training data must contain rows on both sides of the chronological cutoff.")

    x_train = make_features(train["pickup_hour"], train["borough"], origin)
    x_test = make_features(test["pickup_hour"], test["borough"], origin)
    model = HistGradientBoostingRegressor(
        loss="poisson", learning_rate=0.08, max_iter=250,
        max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=0.2,
        random_state=42,
    )
    model.fit(x_train, train["trip_count"].to_numpy())
    prediction = np.maximum(0, model.predict(x_test))
    actual = test["trip_count"].to_numpy(dtype=float)
    mae = float(np.mean(np.abs(actual - prediction)))
    wape = float(np.abs(actual - prediction).sum() / max(actual.sum(), 1) * 100)

    seasonal = train.assign(
        day_of_week=train["pickup_hour"].dt.dayofweek,
        hour=train["pickup_hour"].dt.hour,
    ).groupby(["borough", "day_of_week", "hour"])["trip_count"].mean()
    seasonal_default = train.groupby("borough")["trip_count"].mean()
    baseline_prediction = np.asarray([
        seasonal.get(
            (row.borough, row.pickup_hour.dayofweek, row.pickup_hour.hour),
            seasonal_default.get(row.borough, train["trip_count"].mean()),
        )
        for row in test.itertuples()
    ])
    baseline_mae = float(np.mean(np.abs(actual - baseline_prediction)))
    baseline_wape = float(np.abs(actual - baseline_prediction).sum() / max(actual.sum(), 1) * 100)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": model,
        "origin": origin,
        "feature_columns": FEATURE_COLUMNS,
        "residual_std": float(np.std(actual - prediction)),
        "trained_through": frame["pickup_hour"].max().isoformat(),
        "cutoff": pd.Timestamp(cutoff).isoformat(),
    }
    joblib.dump(artifact, MODEL_FILE)
    metrics = {
        "model": "HistGradientBoostingRegressor",
        "training_rows": int(len(train)),
        "test_rows": int(len(test)),
        "holdout_start": pd.Timestamp(cutoff).isoformat(),
        "mae_trips": round(mae, 2),
        "wape_percent": round(wape, 2),
        "seasonal_baseline_mae_trips": round(baseline_mae, 2),
        "seasonal_baseline_wape_percent": round(baseline_wape, 2),
        "beats_seasonal_baseline": bool(wape < baseline_wape),
        "trained_through": artifact["trained_through"],
    }
    METRICS_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def predict(times: Iterable[datetime], borough: str = "All Boroughs") -> Optional[pd.DataFrame]:
    """Load the saved model and predict hourly demand; return None when unavailable."""
    if not MODEL_FILE.exists():
        return None
    artifact = joblib.load(MODEL_FILE)
    timestamps = list(times)
    borough_name = "All Boroughs" if not borough else borough
    features = make_features(timestamps, [borough_name] * len(timestamps), artifact["origin"])
    values = np.maximum(0, artifact["model"].predict(features))
    spread = max(float(artifact.get("residual_std", 0)), 1.0)
    result = pd.DataFrame({
        "forecast_time": timestamps,
        "predicted_trips": np.rint(values).astype(int),
        "lower_bound": np.rint(np.maximum(0, values - 1.28 * spread)).astype(int),
        "upper_bound": np.rint(values + 1.28 * spread).astype(int),
        "forecast_method": "Gradient-boosting ML model",
    })
    result.attrs.update({"method": "Gradient-boosting ML model", "trained_through": artifact["trained_through"]})
    return result
