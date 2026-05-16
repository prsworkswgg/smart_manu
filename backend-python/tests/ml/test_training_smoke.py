from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_training_smoke_creates_artifacts(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    db = tmp_path / "smoke.db"
    csv_dir = tmp_path / "csv"
    processed = tmp_path / "processed.csv"
    model_dir = tmp_path / "models"
    monkeypatch.setenv("SMOP_DB_PATH", str(db))
    monkeypatch.setenv("SMOP_MODEL_DIR", str(model_dir))
    monkeypatch.setenv("PYTHONPATH", str(root / "backend-python" / "src"))

    gen = subprocess.run([
        sys.executable, str(root / "scripts" / "generate_synthetic_factory_data.py"),
        "--start-date", "2026-05-01T06:00:00", "--hours", "12", "--interval-minutes", "15",
        "--lines", "2", "--machines-per-line", "2", "--profile", "high_load_stress", "--seed", "7",
        "--output-db", str(db), "--output-csv-dir", str(csv_dir), "--reset"
    ], cwd=root, text=True, capture_output=True, timeout=60)
    assert gen.returncode == 0, gen.stderr

    prep = subprocess.run([
        sys.executable, str(root / "backend-python" / "src" / "data" / "preprocessing.py"),
        "--db-path", str(db), "--output", str(processed), "--join-tolerance-minutes", "30"
    ], cwd=root, text=True, capture_output=True, timeout=60)
    assert prep.returncode == 0, prep.stderr

    train = subprocess.run([
        sys.executable, str(root / "backend-python" / "src" / "models" / "train_all.py"),
        "--db-path", str(db), "--processed-csv", str(processed), "--no-rebuild-dataset"
    ], cwd=root, text=True, capture_output=True, timeout=120)
    assert train.returncode == 0, train.stderr
    assert (model_dir / "failure_classifier.joblib").exists()
    assert (model_dir / "rul_regressor.joblib").exists()
    assert (model_dir / "anomaly_detector.joblib").exists()
    assert (model_dir / "failure_classifier_metrics.json").exists()


def test_training_metadata_records_feature_list(temp_db, tmp_path, monkeypatch):
    from database import repository
    run_id = repository.insert_model_run(
        model_name="x", model_type="dummy", model_version="v1", artifact_path="models/x.joblib",
        metrics={"a": 1}, feature_columns=["vibration_rms", "tool_wear"], training_rows=10, test_rows=2, db_path=temp_db
    )
    rows = repository.list_model_runs(temp_db)
    assert run_id > 0
    assert "vibration_rms" in rows[0]["feature_columns_json"]
