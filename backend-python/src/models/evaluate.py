"""Evaluation helpers for classification, regression, and anomaly detection."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)


def safe_float(value: Any) -> float | None:
    """Convert numeric metric to JSON-safe float."""
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return float(value)
    except Exception:
        return None


def classification_metrics(y_true: np.ndarray, y_probability: np.ndarray, threshold: float = 0.5) -> dict[str, Any]:
    """Calculate robust classification metrics."""
    y_pred = (y_probability >= threshold).astype(int)
    labels = [0, 1]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    false_negative_count = int(cm[1, 0]) if cm.shape == (2, 2) else 0

    metrics = {
        "threshold": float(threshold),
        "accuracy": safe_float(accuracy_score(y_true, y_pred)),
        "precision": safe_float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": safe_float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": safe_float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "false_negative_count": false_negative_count,
    }

    try:
        metrics["roc_auc"] = safe_float(roc_auc_score(y_true, y_probability)) if len(np.unique(y_true)) > 1 else None
    except Exception:
        metrics["roc_auc"] = None

    try:
        metrics["pr_auc"] = safe_float(average_precision_score(y_true, y_probability)) if len(np.unique(y_true)) > 1 else None
    except Exception:
        metrics["pr_auc"] = None

    return metrics


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Calculate regression metrics.

    RMSE is computed manually for compatibility with scikit-learn builds where
    mean_squared_error does not expose the ``squared`` keyword.
    """
    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    return {
        "mae": safe_float(mean_absolute_error(y_true, y_pred)),
        "rmse": safe_float(rmse),
        "r2": safe_float(r2_score(y_true, y_pred)),
    }


def anomaly_metrics(anomaly_scores: np.ndarray, anomaly_flags: np.ndarray) -> dict[str, Any]:
    """Return summary metrics for anomaly detection."""
    return {
        "anomaly_count": int(np.sum(anomaly_flags)),
        "row_count": int(len(anomaly_flags)),
        "anomaly_rate": safe_float(float(np.mean(anomaly_flags)) if len(anomaly_flags) else 0.0),
        "score_min": safe_float(np.min(anomaly_scores) if len(anomaly_scores) else None),
        "score_mean": safe_float(np.mean(anomaly_scores) if len(anomaly_scores) else None),
        "score_max": safe_float(np.max(anomaly_scores) if len(anomaly_scores) else None),
    }
