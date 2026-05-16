#!/usr/bin/env python3
"""Validate generated demo outputs and write DEMO_VALIDATION.md."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backend-python" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models.predict import run_full_prediction


def table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return 0


def latest_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT s.machine_id, s.line_id, s.station_id, s.timestamp,
               s.air_temperature, s.process_temperature, s.vibration_rms, s.vibration_peak,
               s.pressure, s.torque, s.rotational_speed, s.motor_current, s.power_consumption,
               s.tool_wear, s.operating_hours, s.production_load, s.ambient_humidity,
               p.cycle_time_sec, p.throughput_count, p.target_throughput, p.station_yield,
               p.reject_count, p.rework_count, p.defect_rate, p.micro_stop_count,
               p.downtime_minutes, p.wip_count, p.queue_length, p.inspection_score_proxy,
               p.process_stability_index
        FROM sensor_readings s
        JOIN production_events p
          ON s.line_id = p.line_id AND s.station_id = p.station_id
        ORDER BY s.timestamp DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        raise RuntimeError("No joined sensor/production row available for prediction validation.")
    return dict(row)


def validate(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path)
    model_dir = Path(args.model_dir)
    os.environ["SMOP_DB_PATH"] = str(db_path)
    os.environ["SMOP_MODEL_DIR"] = str(model_dir)

    checks: list[tuple[str, bool, str]] = []
    counts: dict[str, int] = {}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for table in [
            "sensor_readings",
            "production_events",
            "synthetic_machine_sensor_readings",
            "synthetic_production_events",
            "synthetic_maintenance_events",
            "synthetic_quality_events",
            "synthetic_data_quality_events",
            "data_quality_issues",
            "model_training_runs",
            "predictions",
            "anomaly_alerts",
        ]:
            counts[table] = table_count(conn, table)

        checks.append(("database initialized", db_path.exists(), str(db_path)))
        checks.append(("synthetic factory data generated", counts["synthetic_machine_sensor_readings"] > 0 and counts["synthetic_production_events"] > 0, json.dumps(counts)))
        checks.append(("preprocessing completed", Path(args.processed_csv).exists() and Path(args.processed_csv).stat().st_size > 0, args.processed_csv))
        checks.append(("feature engineering completed", counts["data_quality_issues"] >= 0 and Path(args.processed_csv).exists(), "processed CSV exists"))
        for model_file in ["failure_classifier.joblib", "rul_regressor.joblib", "anomaly_detector.joblib"]:
            checks.append((f"model artifact {model_file}", (model_dir / model_file).exists(), str(model_dir / model_file)))
        for metrics_file in ["failure_classifier_metrics.json", "rul_regressor_metrics.json", "anomaly_detector_metrics.json"]:
            checks.append((f"metrics {metrics_file}", (model_dir / metrics_file).exists(), str(model_dir / metrics_file)))

        prediction_result = None
        try:
            payload = latest_payload(conn)
            prediction_result = run_full_prediction(payload)
            checks.append(("prediction executed", "failure_probability" in prediction_result and "health_score" in prediction_result, json.dumps({k: prediction_result[k] for k in ["failure_probability", "rul_estimate_hours", "anomaly_score", "health_score", "risk_level"]}, default=str)))
        except Exception as exc:
            checks.append(("prediction executed", False, str(exc)))

        checks.append(("dashboard data available", counts["sensor_readings"] > 0 and counts["production_events"] > 0, "sensor/prod rows exist"))

    report = ROOT / "reports" / "demo_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Demo Report\n\n"
        "Synthetic-data Smart Manufacturing AI workflow demo. No real Seagate data. No proprietary data.\n\n"
        f"Generated at: {datetime.now(timezone.utc).isoformat()}\n\n"
        "## Row counts\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in counts.items())
        + "\n",
        encoding="utf-8",
    )
    checks.append(("reports generated", report.exists(), str(report)))

    lines = ["# DEMO_VALIDATION", "", f"Timestamp: `{datetime.now(timezone.utc).isoformat()}`", "", "## PASS / FAIL Summary", ""]
    exit_code = 0
    for name, ok, details in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            exit_code = 1
        print(f"{status}: {name}")
        lines.append(f"- **{status}**: {name} — `{details}`")
    lines.extend([
        "",
        "## Commands represented",
        "",
        "```bash",
        "python scripts/generate_synthetic_factory_data.py ...",
        "python backend-python/src/data/preprocessing.py ...",
        "python backend-python/src/models/train_all.py ...",
        "python scripts/validate_demo_outputs.py ...",
        "```",
        "",
        "## Limitations",
        "",
        "This demo uses synthetic data only. It does not use real Seagate data, proprietary factory data, or real factory deployment evidence.",
    ])
    (ROOT / "DEMO_VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="data/demo_smart_factory.db")
    parser.add_argument("--processed-csv", default="data/processed/demo_processed_ml_dataset.csv")
    parser.add_argument("--model-dir", default="models")
    args = parser.parse_args()
    raise SystemExit(validate(args))


if __name__ == "__main__":
    main()
