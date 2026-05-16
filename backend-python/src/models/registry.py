"""Model registry utilities backed by SQLite and local files."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import sys

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository


def utc_version(prefix: str) -> str:
    """Create a stable timestamp-based model version."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}"


def model_dir() -> Path:
    """Return model artifact directory."""
    import os
    path = Path(os.environ.get("SMOP_MODEL_DIR") or os.environ.get("ARTIFACTS_DIR") or repository.project_root() / "models")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_metrics_json(metrics: dict[str, Any], path: str | Path) -> Path:
    """Write metrics JSON to disk."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def register_model_run(
    model_name: str,
    model_type: str,
    model_version: str,
    artifact_path: str | Path,
    metrics_path: str | Path,
    metrics: dict[str, Any],
    feature_columns: Sequence[str],
    training_rows: int,
    test_rows: int,
    db_path: str | Path | None = None,
) -> int:
    """Register a trained model in SQLite."""
    return repository.insert_model_run(
        model_name=model_name,
        model_type=model_type,
        model_version=model_version,
        artifact_path=str(artifact_path),
        metrics=metrics,
        feature_columns=list(feature_columns),
        training_rows=training_rows,
        test_rows=test_rows,
        metrics_path=str(metrics_path),
        db_path=db_path,
    )


def list_model_runs(db_path: str | Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent model registry rows."""
    return repository.list_model_runs(db_path=db_path, limit=limit)
