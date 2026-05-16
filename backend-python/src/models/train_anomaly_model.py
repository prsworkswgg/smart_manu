"""Train process anomaly detection model using IsolationForest."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository
from features.feature_engineering import FEATURE_COLUMNS, assert_no_leakage
from models.evaluate import anomaly_metrics
from models.registry import model_dir, register_model_run, utc_version, write_metrics_json


def feature_matrix(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """Return X matrix with required features present."""
    out = df.copy()
    for col in feature_columns:
        if col not in out.columns:
            out[col] = 0.0
    return out[feature_columns]


def train_anomaly_model(
    processed_csv: str | Path,
    db_path: str | Path | None = None,
    contamination: float = 0.04,
) -> dict[str, Any]:
    """Train IsolationForest, save artifact, and generate anomaly alerts."""
    df = pd.read_csv(processed_csv)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    feature_columns = [c for c in FEATURE_COLUMNS if c in df.columns]
    assert_no_leakage(feature_columns)
    X = feature_matrix(df, feature_columns)

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                IsolationForest(
                    n_estimators=100,
                    contamination=contamination,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(X)
    raw_scores = model.named_steps["model"].score_samples(model.named_steps["imputer"].transform(X))
    predictions = model.named_steps["model"].predict(model.named_steps["imputer"].transform(X))
    anomaly_flags = (predictions == -1).astype(int)

    metrics = anomaly_metrics(raw_scores, anomaly_flags)
    version = utc_version("anomaly_detector")
    artifact_path = model_dir() / "anomaly_detector.joblib"
    metrics_path = model_dir() / "anomaly_detector_metrics.json"

    bundle = {
        "model_name": "anomaly_detector",
        "model_type": "isolation_forest",
        "model_version": version,
        "model": model,
        "feature_columns": feature_columns,
        "contamination": contamination,
        "metrics": metrics,
        "trained_at": pd.Timestamp.utcnow().isoformat(),
    }
    joblib.dump(bundle, artifact_path)

    write_metrics_json(metrics, metrics_path)

    run_id = register_model_run(
        model_name="anomaly_detector",
        model_type="isolation_forest",
        model_version=version,
        artifact_path=artifact_path,
        metrics_path=metrics_path,
        metrics=metrics,
        feature_columns=feature_columns,
        training_rows=len(df),
        test_rows=0,
        db_path=db_path,
    )

    alert_count = generate_anomaly_alerts(df, raw_scores, anomaly_flags, db_path=db_path)

    return {
        "run_id": run_id,
        "artifact_path": str(artifact_path),
        "metrics_path": str(metrics_path),
        "metrics": metrics,
        "alerts_generated": alert_count,
    }


def generate_anomaly_alerts(
    df: pd.DataFrame,
    anomaly_scores: Any,
    anomaly_flags: Any,
    db_path: str | Path | None = None,
    limit: int = 100,
) -> int:
    """Save anomaly alerts for the most anomalous rows."""
    flagged = df.copy()
    flagged["anomaly_score"] = anomaly_scores
    flagged["anomaly_flag"] = anomaly_flags
    flagged = flagged[flagged["anomaly_flag"] == 1].sort_values("anomaly_score").head(limit)

    count = 0
    for _, row in flagged.iterrows():
        repository.insert_anomaly_alert(
            {
                "machine_id": row.get("machine_id"),
                "line_id": row.get("line_id"),
                "station_id": row.get("station_id"),
                "timestamp": row.get("timestamp").isoformat() if hasattr(row.get("timestamp"), "isoformat") else str(row.get("timestamp")),
                "anomaly_score": float(row.get("anomaly_score")),
                "severity": "high" if row.get("anomaly_score") < -0.15 else "medium",
                "message": "IsolationForest process anomaly detected in simulated manufacturing data.",
                "source": "training_pipeline",
            },
            db_path=db_path,
        )
        count += 1
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train anomaly detection model.")
    parser.add_argument("--input", default="data/processed/processed_ml_dataset.csv")
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--contamination", type=float, default=0.04)
    args = parser.parse_args()
    print(train_anomaly_model(args.input, db_path=args.db_path, contamination=args.contamination))
