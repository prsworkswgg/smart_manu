"""Model artifact loading utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib

import sys

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository


class ModelNotTrainedError(RuntimeError):
    """Raised when an expected model artifact is missing."""


MODEL_FILES = {
    "failure_classifier": "failure_classifier.joblib",
    "rul_regressor": "rul_regressor.joblib",
    "anomaly_detector": "anomaly_detector.joblib",
}


def get_model_dir() -> Path:
    """Return model directory from env or repository default."""
    return Path(os.environ.get("SMOP_MODEL_DIR") or os.environ.get("ARTIFACTS_DIR") or repository.project_root() / "models")


def model_path(model_name: str) -> Path:
    """Return artifact path for known model name."""
    if model_name not in MODEL_FILES:
        raise ValueError(f"Unknown model name: {model_name}")
    return get_model_dir() / MODEL_FILES[model_name]


def load_model_bundle(model_name: str) -> dict[str, Any]:
    """Load a joblib model bundle or raise readable error."""
    path = model_path(model_name)
    if not path.exists():
        raise ModelNotTrainedError(
            f"Model '{model_name}' has not been trained. Expected artifact: {path}. "
            "Run: python backend-python/src/models/train_all.py"
        )
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "model" not in bundle or "feature_columns" not in bundle:
        raise ModelNotTrainedError(f"Artifact for model '{model_name}' is invalid: {path}")
    return bundle
