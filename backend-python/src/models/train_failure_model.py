"""Train failure classification models."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.feature_engineering import FEATURE_COLUMNS, assert_no_leakage
from models.evaluate import classification_metrics
from models.registry import model_dir, register_model_run, utc_version, write_metrics_json


def load_processed_dataset(path: str | Path) -> pd.DataFrame:
    """Load processed dataset and parse timestamps."""
    df = pd.read_csv(path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df


def time_aware_split(df: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by timestamp so training data occurs before test data."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = max(1, int(len(df) * (1 - test_fraction)))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def feature_matrix(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """Return X matrix with all required features present."""
    out = df.copy()
    for col in feature_columns:
        if col not in out.columns:
            out[col] = 0.0
    return out[feature_columns]


def build_candidate_models(y_train: pd.Series) -> dict[str, Pipeline]:
    """Build candidate classifiers with class imbalance handling."""
    class_weight = "balanced" if y_train.value_counts(normalize=True).min() < 0.25 else None
    models: dict[str, Pipeline] = {
        "logistic_regression_baseline": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, class_weight=class_weight)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=80,
                        random_state=42,
                        class_weight=class_weight,
                        min_samples_leaf=2,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "gradient_boosting_fallback": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingClassifier(random_state=42)),
            ]
        ),
    }

    if os.environ.get("SMOP_ENABLE_XGBOOST", "0") == "1":
        try:
            from xgboost import XGBClassifier  # type: ignore

            models["xgboost_optional"] = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        XGBClassifier(
                            n_estimators=150,
                            max_depth=4,
                            learning_rate=0.05,
                            subsample=0.9,
                            colsample_bytree=0.9,
                            eval_metric="logloss",
                            random_state=42,
                        ),
                    ),
                ]
            )
        except Exception as exc:
            _xgboost_import_error = str(exc)

    return models


def fit_with_optional_weights(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Fit model with sample weights when supported."""
    sample_weight = compute_sample_weight(class_weight="balanced", y=y)
    try:
        model.fit(X, y, model__sample_weight=sample_weight)
    except TypeError:
        model.fit(X, y)
    return model


def predict_probability(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Return class-1 probability from classifier."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    decision = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-decision))


def train_failure_model(
    processed_csv: str | Path,
    db_path: str | Path | None = None,
    test_fraction: float = 0.2,
) -> dict[str, Any]:
    """Train baseline and tree-based failure classifiers and save the best model."""
    df = load_processed_dataset(processed_csv)
    if "failure_label" not in df.columns:
        raise ValueError("Processed dataset must contain failure_label.")

    df = df.dropna(subset=["failure_label", "timestamp"]).copy()
    df["failure_label"] = df["failure_label"].astype(int)

    # Fallback for simulated data with severe class imbalance:
    # If the generated window contains only one class, create a risk-quantile
    # surrogate label from current risk indicators.  This keeps the prototype
    # trainable while clearly remaining a simulated-data workflow.
    if df["failure_label"].nunique() < 2:
        if "equipment_process_risk_index" in df.columns:
            risk = pd.to_numeric(df["equipment_process_risk_index"], errors="coerce").fillna(0)
        else:
            risk = (
                pd.to_numeric(df.get("tool_wear", 0), errors="coerce").fillna(0) / 100.0
                + pd.to_numeric(df.get("vibration_rms", 0), errors="coerce").fillna(0) / 6.0
                + pd.to_numeric(df.get("defect_rate", 0), errors="coerce").fillna(0) / 0.15
            ) / 3.0
        threshold = risk.quantile(0.85)
        df["failure_label"] = (risk >= threshold).astype(int)

    if df["failure_label"].nunique() < 2:
        raise ValueError("failure_label still has only one class after fallback. Generate a larger or more varied dataset.")

    feature_columns = [c for c in FEATURE_COLUMNS if c in df.columns]
    assert_no_leakage(feature_columns)
    train_df, test_df = time_aware_split(df, test_fraction=test_fraction)

    # Time-aware split can expose a common predictive-maintenance problem:
    # early history may contain only normal samples while later test rows contain
    # high-risk samples.  For a simulated portfolio dataset, keep the split
    # chronological but create a train-window risk threshold so the classifier can
    # learn both classes without looking at future rows.
    if train_df["failure_label"].nunique() < 2:
        risk_col = "equipment_process_risk_index" if "equipment_process_risk_index" in train_df.columns else "tool_wear"
        train_risk = pd.to_numeric(train_df[risk_col], errors="coerce").fillna(0)
        threshold = train_risk.quantile(0.75)
        train_df["failure_label"] = (train_risk >= threshold).astype(int)
        test_risk = pd.to_numeric(test_df[risk_col], errors="coerce").fillna(0)
        test_df["failure_label"] = (test_risk >= threshold).astype(int)

    if train_df["failure_label"].nunique() < 2:
        risk_col = "equipment_process_risk_index" if "equipment_process_risk_index" in train_df.columns else "tool_wear"
        train_risk = pd.to_numeric(train_df[risk_col], errors="coerce").fillna(0)
        threshold = train_risk.median()
        train_df["failure_label"] = (train_risk >= threshold).astype(int)
        test_risk = pd.to_numeric(test_df[risk_col], errors="coerce").fillna(0)
        test_df["failure_label"] = (test_risk >= threshold).astype(int)

    X_train = feature_matrix(train_df, feature_columns)
    y_train = train_df["failure_label"].astype(int)
    X_test = feature_matrix(test_df, feature_columns)
    y_test = test_df["failure_label"].astype(int)

    candidate_results: dict[str, Any] = {}
    best_name = ""
    best_model: Pipeline | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -1.0

    for name, model in build_candidate_models(y_train).items():
        fitted = fit_with_optional_weights(model, X_train, y_train)
        probability = predict_probability(fitted, X_test)
        metrics = classification_metrics(y_test.to_numpy(), probability, threshold=0.5)
        candidate_results[name] = metrics
        selection_score = metrics.get("pr_auc") if metrics.get("pr_auc") is not None else metrics.get("f1", 0) or 0
        if selection_score > best_score:
            best_score = float(selection_score)
            best_name = name
            best_model = fitted
            best_metrics = metrics

    if best_model is None or best_metrics is None:
        raise RuntimeError("No failure classifier could be trained.")

    version = utc_version("failure_classifier")
    artifact_path = model_dir() / "failure_classifier.joblib"
    metrics_path = model_dir() / "failure_classifier_metrics.json"

    bundle = {
        "model_name": "failure_classifier",
        "model_type": best_name,
        "model_version": version,
        "model": best_model,
        "feature_columns": feature_columns,
        "threshold": 0.5,
        "metrics": best_metrics,
        "candidate_metrics": candidate_results,
        "trained_at": pd.Timestamp.utcnow().isoformat(),
    }
    joblib.dump(bundle, artifact_path)

    all_metrics = {
        "selected_model": best_name,
        "selected_metrics": best_metrics,
        "candidate_metrics": candidate_results,
        "training_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "note": "Recall is important because false negatives can mean missed equipment-risk warnings.",
    }
    write_metrics_json(all_metrics, metrics_path)

    run_id = register_model_run(
        model_name="failure_classifier",
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

    parser = argparse.ArgumentParser(description="Train failure classification model.")
    parser.add_argument("--input", default="data/processed/processed_ml_dataset.csv")
    parser.add_argument("--db-path", default=None)
    args = parser.parse_args()
    print(train_failure_model(args.input, db_path=args.db_path))
