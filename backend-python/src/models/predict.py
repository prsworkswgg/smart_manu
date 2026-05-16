"""Prediction helpers used by FastAPI and offline scripts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from diagnostics.hint_engine import generate_diagnostic_hint
from features.feature_engineering import FEATURE_COLUMNS, add_engineered_features, assert_no_leakage
from health_score.scoring import compute_health_score, feature_based_scores
from models.model_loader import load_model_bundle


def payload_to_feature_frame(payload: dict[str, Any], feature_columns: list[str] | None = None) -> pd.DataFrame:
    """Convert a single inference payload into a feature DataFrame.

    If engineered features are absent, they are generated using the same feature
    function.  Rolling features degrade gracefully to current/fallback values for
    single-row inference.
    """
    row = dict(payload)
    if "timestamp" not in row or row["timestamp"] is None:
        row["timestamp"] = pd.Timestamp.utcnow().isoformat()

    df = pd.DataFrame([row])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # When inference payload does not include production fields, add safe defaults.
    defaults = {
        "cycle_time_sec": 0.0,
        "throughput_count": 0,
        "target_throughput": 1,
        "station_yield": 1.0,
        "reject_count": 0,
        "rework_count": 0,
        "defect_rate": 0.0,
        "micro_stop_count": 0,
        "downtime_minutes": 0.0,
        "wip_count": 0,
        "queue_length": 0,
        "inspection_score_proxy": 1.0,
        "process_stability_index": 1.0,
        "join_lag_seconds": 0.0,
    }
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value

    if "event_timestamp" not in df.columns:
        df["event_timestamp"] = df["timestamp"]
    if "sensor_timestamp" not in df.columns:
        df["sensor_timestamp"] = df["timestamp"]

    featured = add_engineered_features(df)
    required = feature_columns or FEATURE_COLUMNS
    assert_no_leakage(required)
    for col in required:
        if col not in featured.columns:
            featured[col] = 0.0
    return featured


def _predict_probability(model: Any, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    decision = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-decision))


def predict_failure(payload: dict[str, Any]) -> dict[str, Any]:
    """Predict failure probability using trained failure classifier."""
    bundle = load_model_bundle("failure_classifier")
    features = payload_to_feature_frame(payload, bundle["feature_columns"])
    X = features[bundle["feature_columns"]]
    probability = float(_predict_probability(bundle["model"], X)[0])
    return {
        "failure_probability": probability,
        "model_version": bundle.get("model_version", "unknown"),
        "features": features.iloc[0].to_dict(),
    }


def predict_rul(payload: dict[str, Any]) -> dict[str, Any]:
    """Predict RUL hours using trained regressor."""
    bundle = load_model_bundle("rul_regressor")
    features = payload_to_feature_frame(payload, bundle["feature_columns"])
    X = features[bundle["feature_columns"]]
    prediction = float(bundle["model"].predict(X)[0])
    return {
        "rul_estimate_hours": max(0.0, prediction),
        "model_version": bundle.get("model_version", "unknown"),
        "features": features.iloc[0].to_dict(),
    }


def detect_anomaly(payload: dict[str, Any]) -> dict[str, Any]:
    """Detect anomaly using trained IsolationForest."""
    bundle = load_model_bundle("anomaly_detector")
    features = payload_to_feature_frame(payload, bundle["feature_columns"])
    X = features[bundle["feature_columns"]]
    model = bundle["model"]
    transformed = model.named_steps["imputer"].transform(X)
    isolation = model.named_steps["model"]
    score = float(isolation.score_samples(transformed)[0])
    flag = int(isolation.predict(transformed)[0] == -1)
    return {
        "anomaly_score": score,
        "anomaly_flag": flag,
        "model_version": bundle.get("model_version", "unknown"),
        "features": features.iloc[0].to_dict(),
    }


def run_full_prediction(payload: dict[str, Any]) -> dict[str, Any]:
    """Run failure, RUL, anomaly, health score, and diagnostic hint."""
    failure_result = predict_failure(payload)
    rul_result = predict_rul(payload)
    anomaly_result = detect_anomaly(payload)

    features = failure_result["features"]
    feature_scores = feature_based_scores(features)
    health = compute_health_score(
        failure_probability=failure_result["failure_probability"],
        anomaly_score=anomaly_result["anomaly_score"],
        tool_wear_index=feature_scores["tool_wear_index"],
        process_drift_score=feature_scores["process_drift_score"],
        data_quality_penalty=feature_scores["data_quality_penalty"],
        rul_estimate_hours=rul_result["rul_estimate_hours"],
    )
    hint = generate_diagnostic_hint(
        features,
        failure_probability=failure_result["failure_probability"],
        anomaly_score=anomaly_result["anomaly_score"],
    )

    return {
        "failure_probability": failure_result["failure_probability"],
        "rul_estimate_hours": rul_result["rul_estimate_hours"],
        "anomaly_score": anomaly_result["anomaly_score"],
        "anomaly_flag": anomaly_result["anomaly_flag"],
        "health_score": health["health_score"],
        "risk_level": health["risk_level"],
        "recommended_action": hint.get("recommended_action") or health["recommended_action"],
        "diagnostic_hint": hint["diagnostic_hint"],
        "model_version": {
            "failure_classifier": failure_result["model_version"],
            "rul_regressor": rul_result["model_version"],
            "anomaly_detector": anomaly_result["model_version"],
        },
        "risk_components": health["risk_components"],
        "features": features,
    }
