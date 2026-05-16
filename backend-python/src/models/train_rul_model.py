"""Train Remaining Useful Life (RUL) regression model."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.feature_engineering import FEATURE_COLUMNS, assert_no_leakage
from models.evaluate import regression_metrics
from models.registry import model_dir, register_model_run, utc_version, write_metrics_json


def time_aware_split(df: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by timestamp to avoid future-data leakage."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = max(1, int(len(df) * (1 - test_fraction)))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def feature_matrix(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """Return X matrix with required columns."""
    out = df.copy()
    for col in feature_columns:
        if col not in out.columns:
            out[col] = 0.0
    return out[feature_columns]


def train_rul_model(
    processed_csv: str | Path,
    db_path: str | Path | None = None,
    test_fraction: float = 0.2,
) -> dict[str, Any]:
    """Train RUL regression models and save the best one."""
    df = pd.read_csv(processed_csv)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    if "rul_estimate_hours" not in df.columns:
        raise ValueError("Processed dataset must contain rul_estimate_hours.")

    df = df.dropna(subset=["rul_estimate_hours", "timestamp"]).copy()
    feature_columns = [c for c in FEATURE_COLUMNS if c in df.columns]
    assert_no_leakage(feature_columns)
    train_df, test_df = time_aware_split(df, test_fraction=test_fraction)
    X_train = feature_matrix(train_df, feature_columns)
    y_train = train_df["rul_estimate_hours"]
    X_test = feature_matrix(test_df, feature_columns)
    y_test = test_df["rul_estimate_hours"]

    candidates: dict[str, Pipeline] = {
        "random_forest_regressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=80,
                        random_state=42,
                        min_samples_leaf=2,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "gradient_boosting_regressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingRegressor(random_state=42)),
            ]
        ),
    }

    best_name = ""
    best_model: Pipeline | None = None
    best_metrics: dict[str, Any] | None = None
    candidate_metrics: dict[str, Any] = {}
    best_mae = float("inf")

    for name, model in candidates.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        metrics = regression_metrics(y_test.to_numpy(), pred)
        candidate_metrics[name] = metrics
        mae = metrics["mae"] if metrics["mae"] is not None else float("inf")
        if mae < best_mae:
            best_mae = float(mae)
            best_name = name
            best_model = model
            best_metrics = metrics

    if best_model is None or best_metrics is None:
        raise RuntimeError("No RUL regressor could be trained.")

    version = utc_version("rul_regressor")
    artifact_path = model_dir() / "rul_regressor.joblib"
    metrics_path = model_dir() / "rul_regressor_metrics.json"

    bundle = {
        "model_name": "rul_regressor",
        "model_type": best_name,
        "model_version": version,
        "model": best_model,
        "feature_columns": feature_columns,
        "metrics": best_metrics,
        "candidate_metrics": candidate_metrics,
        "trained_at": pd.Timestamp.utcnow().isoformat(),
        "note": "RUL is simulated and not validated on real machines.",
    }
    joblib.dump(bundle, artifact_path)

    all_metrics = {
        "selected_model": best_name,
        "selected_metrics": best_metrics,
        "candidate_metrics": candidate_metrics,
        "training_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "note": "RUL is simulated and not validated on real machines.",
    }
    write_metrics_json(all_metrics, metrics_path)

    run_id = register_model_run(
        model_name="rul_regressor",
        model_type=best_name,
        model_version=version,
        artifact_path=artifact_path,
        metrics_path=metrics_path,
        metrics=all_metrics,
        feature_columns=feature_columns,
        training_rows=len(train_df),
        test_rows=len(test_df),
        db_path=db_path,
    )

    return {
        "run_id": run_id,
        "artifact_path": str(artifact_path),
        "metrics_path": str(metrics_path),
        "metrics": all_metrics,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train RUL regression model.")
    parser.add_argument("--input", default="data/processed/processed_ml_dataset.csv")
    parser.add_argument("--db-path", default=None)
    args = parser.parse_args()
    print(train_rul_model(args.input, db_path=args.db_path))
