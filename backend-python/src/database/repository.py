"""SQLite repository utilities for the Smart Manufacturing AI Operations Platform.

This module intentionally uses the Python standard-library ``sqlite3`` package so
the prototype stays easy to run on Linux, Windows, and WSL.  It creates the core
tables needed by ingestion, data quality, ML training, model registry,
prediction logging, and anomaly alerts.

The project is a simulated-data working prototype.  It does not use real Seagate
or proprietary factory data.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


def project_root() -> Path:
    """Return repository root based on this file location."""
    return Path(__file__).resolve().parents[3]


def default_db_path() -> Path:
    """Return SQLite DB path from env or default repository location."""
    return Path(os.environ.get("SMOP_DB_PATH") or os.environ.get("DATABASE_PATH") or project_root() / "database" / "smart_manufacturing.db")


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a SQLite connection with row dictionaries and foreign keys enabled."""
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def initialize_database(db_path: str | Path | None = None) -> None:
    """Create required SQLite tables if they do not already exist."""
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS machines (
                machine_id TEXT PRIMARY KEY,
                machine_type TEXT,
                line_id TEXT,
                station_id TEXT,
                criticality TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS production_lines (
                line_id TEXT PRIMARY KEY,
                line_name TEXT,
                target_throughput_per_hour INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS stations (
                station_id TEXT PRIMARY KEY,
                line_id TEXT,
                station_name TEXT,
                machine_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                machine_id TEXT NOT NULL,
                line_id TEXT NOT NULL,
                station_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                air_temperature REAL,
                process_temperature REAL,
                vibration_rms REAL,
                vibration_peak REAL,
                pressure REAL,
                torque REAL,
                rotational_speed REAL,
                motor_current REAL,
                power_consumption REAL,
                tool_wear REAL,
                operating_hours REAL,
                production_load REAL,
                ambient_humidity REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_sensor_event_id ON sensor_readings(event_id) WHERE event_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_sensor_station_ts
                ON sensor_readings(machine_id, station_id, timestamp);

            CREATE TABLE IF NOT EXISTS production_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                line_id TEXT NOT NULL,
                station_id TEXT NOT NULL,
                batch_id TEXT,
                shift TEXT,
                timestamp TEXT NOT NULL,
                cycle_time_sec REAL,
                throughput_count INTEGER,
                target_throughput INTEGER,
                station_yield REAL,
                reject_count INTEGER,
                rework_count INTEGER,
                defect_rate REAL,
                micro_stop_count INTEGER,
                downtime_minutes REAL,
                wip_count INTEGER,
                queue_length INTEGER,
                inspection_score_proxy REAL,
                process_stability_index REAL,
                operator_group TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_production_event_id ON production_events(event_id) WHERE event_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_production_station_ts
                ON production_events(line_id, station_id, timestamp);

            CREATE TABLE IF NOT EXISTS data_quality_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                machine_id TEXT,
                line_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                details_json TEXT,
                detected_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS data_acquisition_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                status TEXT,
                message TEXT,
                records_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS maintenance_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT,
                station_id TEXT,
                event_type TEXT,
                event_timestamp TEXT,
                details_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_training_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_type TEXT NOT NULL,
                model_version TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                metrics_json TEXT,
                feature_columns_json TEXT,
                training_rows INTEGER,
                test_rows INTEGER,
                started_at TEXT,
                completed_at TEXT,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                metrics_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT,
                line_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                failure_probability REAL,
                rul_estimate_hours REAL,
                anomaly_score REAL,
                anomaly_flag INTEGER,
                health_score REAL,
                risk_level TEXT,
                recommended_action TEXT,
                diagnostic_hint TEXT,
                model_version TEXT,
                payload_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS anomaly_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT,
                line_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                anomaly_score REAL,
                severity TEXT,
                message TEXT,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS diagnostic_hints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT,
                line_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                hint TEXT,
                recommended_action TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT,
                report_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );



            CREATE TABLE IF NOT EXISTS synthetic_machine_sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                site_id TEXT,
                area_id TEXT,
                line_id TEXT,
                machine_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                shift TEXT,
                load_state TEXT,
                product_family TEXT,
                recipe_id TEXT,
                lot_id TEXT,
                failure_mode TEXT,
                ambient_temperature REAL,
                ambient_humidity REAL,
                cleanroom_particle_proxy REAL,
                machine_age_days REAL,
                hours_since_maintenance REAL,
                hidden_degradation_state REAL,
                tool_wear REAL,
                air_temperature REAL,
                process_temperature REAL,
                vibration_rms REAL,
                vibration_peak REAL,
                pressure REAL,
                torque REAL,
                rotational_speed REAL,
                motor_current REAL,
                power_consumption REAL,
                production_load REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS synthetic_production_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                site_id TEXT,
                area_id TEXT,
                line_id TEXT,
                machine_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                shift TEXT,
                load_state TEXT,
                product_family TEXT,
                recipe_id TEXT,
                lot_id TEXT,
                failure_mode TEXT,
                cycle_time_sec REAL,
                throughput_count INTEGER,
                target_throughput INTEGER,
                station_yield REAL,
                first_pass_yield REAL,
                reject_count INTEGER,
                rework_count INTEGER,
                defect_rate REAL,
                micro_stop_count INTEGER,
                downtime_minutes REAL,
                wip_count INTEGER,
                queue_length INTEGER,
                queue_time_minutes REAL,
                inspection_score_proxy REAL,
                process_stability_index REAL,
                operator_group TEXT,
                failure_label INTEGER,
                rul_target REAL,
                future_failure_window INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS synthetic_maintenance_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                site_id TEXT,
                area_id TEXT,
                line_id TEXT,
                machine_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                maintenance_type TEXT,
                reset_ratio REAL,
                degradation_before REAL,
                degradation_after REAL,
                duration_minutes REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS synthetic_quality_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                site_id TEXT,
                area_id TEXT,
                line_id TEXT,
                machine_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                lot_id TEXT,
                product_family TEXT,
                quality_event_type TEXT,
                severity TEXT,
                defect_rate REAL,
                first_pass_yield REAL,
                affected_units INTEGER,
                duration_minutes REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS synthetic_data_quality_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                site_id TEXT,
                area_id TEXT,
                line_id TEXT,
                machine_id TEXT,
                station_id TEXT,
                timestamp TEXT,
                issue_type TEXT,
                severity TEXT,
                affected_table TEXT,
                affected_column TEXT,
                details_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_synth_sensor_ts
                ON synthetic_machine_sensor_readings(site_id, line_id, machine_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_synth_prod_ts
                ON synthetic_production_events(site_id, line_id, station_id, timestamp);

            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                component TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_machine_ts
                ON predictions(machine_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_predictions_line_risk_ts
                ON predictions(line_id, risk_level, timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_severity_ts
                ON anomaly_alerts(severity, timestamp);
            CREATE INDEX IF NOT EXISTS idx_quality_severity_detected
                ON data_quality_issues(severity, detected_at);

            CREATE VIEW IF NOT EXISTS vw_latest_machine_health AS
            SELECT p.*
            FROM predictions p
            INNER JOIN (
                SELECT machine_id, MAX(timestamp) AS latest_timestamp
                FROM predictions
                WHERE machine_id IS NOT NULL
                GROUP BY machine_id
            ) latest
            ON p.machine_id = latest.machine_id
            AND p.timestamp = latest.latest_timestamp;

            CREATE VIEW IF NOT EXISTS vw_line_operational_summary AS
            SELECT
                pe.line_id,
                COUNT(*) AS production_event_count,
                AVG(pe.cycle_time_sec) AS avg_cycle_time_sec,
                AVG(pe.station_yield) AS avg_station_yield,
                SUM(COALESCE(pe.downtime_minutes, 0)) AS total_downtime_minutes,
                SUM(COALESCE(pe.reject_count, 0)) AS total_reject_count,
                MAX(pe.timestamp) AS latest_production_timestamp
            FROM production_events pe
            GROUP BY pe.line_id;
            """
        )
        conn.commit()


def read_table(table_name: str, db_path: str | Path | None = None, limit: int | None = None) -> pd.DataFrame:
    """Read a full SQLite table into a pandas DataFrame."""
    initialize_database(db_path)
    query = f"SELECT * FROM {table_name}"
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    with connect(db_path) as conn:
        return pd.read_sql_query(query, conn)


def read_sensor_readings(db_path: str | Path | None = None) -> pd.DataFrame:
    """Read sensor readings from SQLite sorted by timestamp."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM sensor_readings ORDER BY timestamp", conn)


def read_production_events(db_path: str | Path | None = None) -> pd.DataFrame:
    """Read production events from SQLite sorted by timestamp."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM production_events ORDER BY timestamp", conn)


def _insert_dict(conn: sqlite3.Connection, table_name: str, row: Mapping[str, Any]) -> int:
    clean = {k: _jsonify_if_needed(v) for k, v in row.items() if v is not None}
    cols = list(clean.keys())
    placeholders = ", ".join(["?"] * len(cols))
    verb = "INSERT OR IGNORE" if clean.get("event_id") is not None else "INSERT"
    sql = f"{verb} INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
    cur = conn.execute(sql, [clean[c] for c in cols])
    return int(cur.lastrowid)


def _jsonify_if_needed(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def insert_sensor_reading(row: Mapping[str, Any], db_path: str | Path | None = None) -> int:
    """Insert a sensor reading dictionary into SQLite."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        row_id = _insert_dict(conn, "sensor_readings", row)
        conn.commit()
        return row_id


def insert_production_event(row: Mapping[str, Any], db_path: str | Path | None = None) -> int:
    """Insert a production event dictionary into SQLite."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        row_id = _insert_dict(conn, "production_events", row)
        conn.commit()
        return row_id


def insert_data_quality_issues(issues: Iterable[Mapping[str, Any]], db_path: str | Path | None = None) -> int:
    """Insert a batch of data quality issues."""
    initialize_database(db_path)
    count = 0
    with connect(db_path) as conn:
        for issue in issues:
            row = dict(issue)
            row.setdefault("detected_at", utc_now_iso())
            if "details" in row and "details_json" not in row:
                row["details_json"] = json.dumps(row.pop("details"), ensure_ascii=False)
            _insert_dict(conn, "data_quality_issues", row)
            count += 1
        conn.commit()
    return count


def insert_model_run(
    model_name: str,
    model_type: str,
    model_version: str,
    artifact_path: str | Path,
    metrics: Mapping[str, Any],
    feature_columns: Sequence[str],
    training_rows: int,
    test_rows: int,
    status: str = "completed",
    metrics_path: str | Path | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Insert a model training run and matching artifact record."""
    initialize_database(db_path)
    now = utc_now_iso()
    with connect(db_path) as conn:
        run_id = _insert_dict(
            conn,
            "model_training_runs",
            {
                "model_name": model_name,
                "model_type": model_type,
                "model_version": model_version,
                "artifact_path": str(artifact_path),
                "metrics_json": json.dumps(metrics, ensure_ascii=False),
                "feature_columns_json": json.dumps(list(feature_columns), ensure_ascii=False),
                "training_rows": training_rows,
                "test_rows": test_rows,
                "started_at": now,
                "completed_at": now,
                "status": status,
            },
        )
        _insert_dict(
            conn,
            "model_artifacts",
            {
                "model_name": model_name,
                "model_version": model_version,
                "artifact_path": str(artifact_path),
                "metrics_path": str(metrics_path) if metrics_path else None,
            },
        )
        conn.commit()
        return run_id


def insert_prediction(row: Mapping[str, Any], db_path: str | Path | None = None) -> int:
    """Insert a prediction record into SQLite."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        row_id = _insert_dict(conn, "predictions", row)
        conn.commit()
        return row_id


def insert_anomaly_alert(row: Mapping[str, Any], db_path: str | Path | None = None) -> int:
    """Insert an anomaly alert into SQLite."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        row_id = _insert_dict(conn, "anomaly_alerts", row)
        conn.commit()
        return row_id


def insert_diagnostic_hint(row: Mapping[str, Any], db_path: str | Path | None = None) -> int:
    """Insert a diagnostic hint into SQLite."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        row_id = _insert_dict(conn, "diagnostic_hints", row)
        conn.commit()
        return row_id


def list_model_runs(db_path: str | Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent model runs."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM model_training_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def list_predictions(db_path: str | Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return recent prediction rows."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def list_alerts(db_path: str | Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return recent anomaly alerts."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM anomaly_alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_data_acquisition_status(db_path: str | Path | None = None) -> dict[str, Any]:
    """Return row counts and latest timestamps for the acquisition pipeline."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        sensor_count = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
        production_count = conn.execute("SELECT COUNT(*) FROM production_events").fetchone()[0]
        latest_sensor = conn.execute("SELECT MAX(timestamp) FROM sensor_readings").fetchone()[0]
        latest_production = conn.execute("SELECT MAX(timestamp) FROM production_events").fetchone()[0]
        quality_count = conn.execute("SELECT COUNT(*) FROM data_quality_issues").fetchone()[0]
    return {
        "sensor_readings": sensor_count,
        "production_events": production_count,
        "data_quality_issues": quality_count,
        "latest_sensor_timestamp": latest_sensor,
        "latest_production_timestamp": latest_production,
    }


def get_line_health(line_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    """Aggregate recent prediction rows for a production line."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT line_id,
                   COUNT(*) AS prediction_count,
                   AVG(health_score) AS avg_health_score,
                   MAX(failure_probability) AS max_failure_probability,
                   MIN(rul_estimate_hours) AS min_rul_estimate_hours,
                   MIN(anomaly_score) AS min_anomaly_score
            FROM predictions
            WHERE line_id = ?
            """,
            (line_id,),
        ).fetchone()
        alerts = conn.execute(
            "SELECT COUNT(*) FROM anomaly_alerts WHERE line_id = ?", (line_id,)
        ).fetchone()[0]
    result = dict(rows) if rows else {"line_id": line_id}
    result["line_id"] = line_id
    result["alert_count"] = alerts
    if result.get("avg_health_score") is None:
        result["risk_level"] = "unknown"
    elif result["avg_health_score"] >= 80:
        result["risk_level"] = "low"
    elif result["avg_health_score"] >= 60:
        result["risk_level"] = "medium"
    elif result["avg_health_score"] >= 40:
        result["risk_level"] = "high"
    else:
        result["risk_level"] = "critical"
    return result



def insert_many(table_name: str, rows: Iterable[Mapping[str, Any]], db_path: str | Path | None = None) -> int:
    """Insert many mapping rows into a SQLite table."""
    initialize_database(db_path)
    count = 0
    with connect(db_path) as conn:
        for row in rows:
            _insert_dict(conn, table_name, row)
            count += 1
        conn.commit()
    return count


def reset_demo_tables(db_path: str | Path | None = None, include_core: bool = True) -> None:
    """Clear demo tables for a deterministic one-command demo run."""
    initialize_database(db_path)
    synthetic_tables = [
        "synthetic_machine_sensor_readings",
        "synthetic_production_events",
        "synthetic_maintenance_events",
        "synthetic_quality_events",
        "synthetic_data_quality_events",
    ]
    core_tables = [
        "sensor_readings",
        "production_events",
        "data_quality_issues",
        "maintenance_events",
        "model_training_runs",
        "model_artifacts",
        "predictions",
        "anomaly_alerts",
        "diagnostic_hints",
        "reports",
        "system_logs",
        "data_acquisition_logs",
    ]
    with connect(db_path) as conn:
        for table in synthetic_tables + (core_tables if include_core else []):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
