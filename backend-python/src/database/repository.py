"""SQLite repository utilities for the Smart Manufacturing AI Operations Platform.

This module intentionally uses the Python standard-library ``sqlite3`` package so
the local DEMO data system stays easy to run on Linux, Windows, and WSL.  It
creates the core tables needed by ingestion, data quality, ML training, model
registry, prediction logging, anomaly alerts, and operations workflow cases.
"""

from __future__ import annotations

import json
import os
import sqlite3
from hashlib import sha1, sha256
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

ROLE_RANK = {"viewer": 1, "operator": 2, "supervisor": 3, "admin": 4}
DEFAULT_ENTERPRISE_USERS = [
    ("viewer", "Operations Viewer", "viewer", "demo-viewer-key"),
    ("operator", "Operations Operator", "operator", "demo-operator-key"),
    ("supervisor", "Operations Supervisor", "supervisor", "demo-supervisor-key"),
]


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

            CREATE TABLE IF NOT EXISTS operational_cases (
                case_id TEXT PRIMARY KEY,
                signal_key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT,
                line_id TEXT,
                station_id TEXT,
                machine_id TEXT,
                source_type TEXT NOT NULL,
                signal_score REAL,
                condition_score REAL,
                first_seen_at TEXT,
                last_seen_at TEXT,
                due_at TEXT,
                next_action TEXT,
                evidence_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS operational_case_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT,
                note TEXT,
                from_status TEXT,
                to_status TEXT,
                payload_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(case_id) REFERENCES operational_cases(case_id)
            );

            CREATE TABLE IF NOT EXISTS work_orders (
                work_order_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT,
                task_summary TEXT,
                external_ref TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(case_id) REFERENCES operational_cases(case_id)
            );

            CREATE TABLE IF NOT EXISTS app_users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                api_key_hash TEXT UNIQUE NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS case_ownership (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                ownership_role TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                assigned_by TEXT,
                assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                released_at TEXT,
                FOREIGN KEY(case_id) REFERENCES operational_cases(case_id),
                FOREIGN KEY(user_id) REFERENCES app_users(user_id)
            );

            CREATE TABLE IF NOT EXISTS case_approvals (
                approval_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                approval_type TEXT NOT NULL,
                requested_by TEXT,
                decided_by TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                decision_note TEXT,
                policy_version TEXT,
                requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                decided_at TEXT,
                FOREIGN KEY(case_id) REFERENCES operational_cases(case_id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                case_id TEXT,
                event_type TEXT NOT NULL,
                recipient TEXT,
                channel TEXT,
                severity TEXT,
                title TEXT,
                body TEXT,
                status TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                delivered_at TEXT,
                FOREIGN KEY(case_id) REFERENCES operational_cases(case_id)
            );

            CREATE TABLE IF NOT EXISTS integration_outbox (
                outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_type TEXT,
                target_system TEXT,
                case_id TEXT,
                work_order_id TEXT,
                status TEXT NOT NULL,
                endpoint_url TEXT,
                payload_json TEXT,
                response_status INTEGER,
                response_body TEXT,
                attempts INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT,
                FOREIGN KEY(case_id) REFERENCES operational_cases(case_id),
                FOREIGN KEY(work_order_id) REFERENCES work_orders(work_order_id)
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
            CREATE INDEX IF NOT EXISTS idx_cases_status_severity
                ON operational_cases(status, severity, last_seen_at);
            CREATE INDEX IF NOT EXISTS idx_case_events_case_created
                ON operational_case_events(case_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_case_ownership_case_active
                ON case_ownership(case_id, active, ownership_role);
            CREATE INDEX IF NOT EXISTS idx_case_approvals_case_status
                ON case_approvals(case_id, approval_type, status);
            CREATE INDEX IF NOT EXISTS idx_notifications_status_created
                ON notifications(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_integration_outbox_status_created
                ON integration_outbox(status, created_at);

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
        _seed_default_users(conn)
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


CASE_STATUSES = {"new", "triage", "assigned", "investigating", "mitigated", "resolved"}
CASE_SEVERITIES = {"low", "medium", "high", "critical"}


def _api_key_hash(api_key: str) -> str:
    return sha256(api_key.encode("utf-8")).hexdigest()


def _seed_default_users(conn: sqlite3.Connection) -> None:
    """Ensure the local enterprise demo users exist for API and workflow policy checks."""
    for user_id, display_name, role, api_key in DEFAULT_ENTERPRISE_USERS:
        conn.execute(
            """
            INSERT INTO app_users (user_id, display_name, role, api_key_hash, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                api_key_hash = excluded.api_key_hash,
                active = 1
            """,
            (user_id, display_name, role, _api_key_hash(api_key), utc_now_iso()),
        )


def authenticate_api_key(api_key: str | None, db_path: str | Path | None = None) -> dict[str, Any] | None:
    """Return the active user for an API key, or None when the key is missing or invalid."""
    if not api_key:
        return None
    initialize_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT user_id, display_name, role, active, created_at
            FROM app_users
            WHERE api_key_hash = ? AND active = 1
            """,
            (_api_key_hash(str(api_key)),),
        ).fetchone()
    return dict(row) if row else None


def user_has_role(user: Mapping[str, Any] | None, required_role: str) -> bool:
    """Return whether a user record satisfies the required role level."""
    if not user:
        return False
    actual_rank = ROLE_RANK.get(str(user.get("role", "")).lower(), 0)
    required_rank = ROLE_RANK.get(str(required_role).lower(), 0)
    return actual_rank >= required_rank


def _get_user(conn: sqlite3.Connection, user_id: str | None) -> dict[str, Any] | None:
    if not user_id:
        return None
    row = conn.execute(
        "SELECT user_id, display_name, role, active, created_at FROM app_users WHERE user_id = ? AND active = 1",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def _require_user_role(conn: sqlite3.Connection, user_id: str | None, required_role: str) -> dict[str, Any]:
    user = _get_user(conn, user_id)
    if not user:
        raise PermissionError(f"Unknown workflow user: {user_id}")
    if not user_has_role(user, required_role):
        raise PermissionError(f"{user_id} requires {required_role} role")
    return user


def _record_id(prefix: str, *parts: Any) -> str:
    source = "|".join(str(part) for part in [prefix, *parts, utc_now_iso()])
    return f"{prefix}-{sha1(source.encode('utf-8')).hexdigest()[:10].upper()}"


def _normalize_case_status(status: str | None) -> str:
    value = str(status or "new").strip().lower()
    return value if value in CASE_STATUSES else "triage"


def _normalize_case_severity(severity: str | None) -> str:
    value = str(severity or "medium").strip().lower()
    if value in {"warning", "warn", "elevated"}:
        return "medium"
    return value if value in CASE_SEVERITIES else "medium"


def _severity_rank(severity: str | None) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(_normalize_case_severity(severity), 2)


def _case_id_from_signal(signal_key: str) -> str:
    return "CASE-" + sha1(signal_key.encode("utf-8")).hexdigest()[:10].upper()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _derive_condition_score(row: Mapping[str, Any]) -> float:
    vibration = _as_float(row.get("vibration_rms"))
    wear = _as_float(row.get("tool_wear"))
    temp = _as_float(row.get("process_temperature"))
    current = _as_float(row.get("motor_current"))
    torque = _as_float(row.get("torque"))
    vibration_penalty = _clamp((vibration - 1.1) / 2.4 * 34.0)
    wear_penalty = _clamp(wear / 100.0 * 28.0)
    temp_penalty = _clamp(max(0.0, temp - 58.0) / 22.0 * 16.0)
    current_penalty = _clamp(max(0.0, current - 8.0) / 12.0 * 12.0)
    torque_penalty = _clamp(max(0.0, torque - 18.0) / 18.0 * 10.0)
    return round(_clamp(100.0 - vibration_penalty - wear_penalty - temp_penalty - current_penalty - torque_penalty), 1)


def _severity_from_condition(condition_score: float, anomaly_index: float) -> str:
    if condition_score < 45 or anomaly_index >= 0.65:
        return "critical"
    if condition_score < 62 or anomaly_index >= 0.45:
        return "high"
    if condition_score < 78 or anomaly_index >= 0.25:
        return "medium"
    return "low"


def _dominant_signal(row: Mapping[str, Any]) -> str:
    candidates = {
        "vibration": _as_float(row.get("vibration_rms")) / 3.4,
        "tool_wear": _as_float(row.get("tool_wear")) / 100.0,
        "temperature": max(0.0, _as_float(row.get("process_temperature")) - 58.0) / 22.0,
        "motor_current": max(0.0, _as_float(row.get("motor_current")) - 8.0) / 12.0,
        "torque": max(0.0, _as_float(row.get("torque")) - 18.0) / 18.0,
    }
    signal, score = max(candidates.items(), key=lambda item: item[1])
    return signal if score > 0.1 else "balanced"


def _due_at_for_severity(last_seen_at: str | None, severity: str) -> str:
    base = pd.Timestamp(last_seen_at) if last_seen_at else pd.Timestamp.utcnow()
    if base.tzinfo is None:
        base = base.tz_localize("UTC")
    hours = {"critical": 2, "high": 4, "medium": 12, "low": 24}.get(_normalize_case_severity(severity), 12)
    return (base + pd.Timedelta(hours=hours)).isoformat()


def _insert_case_event(
    conn: sqlite3.Connection,
    case_id: str,
    event_type: str,
    actor: str = "system",
    note: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO operational_case_events
            (case_id, event_type, actor, note, from_status, to_status, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            event_type,
            actor,
            note,
            from_status,
            to_status,
            json.dumps(payload or {}, ensure_ascii=False),
            utc_now_iso(),
        ),
    )


def _case_has_approved_approval(conn: sqlite3.Connection, case_id: str, approval_type: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM case_approvals
        WHERE case_id = ? AND approval_type = ? AND status = 'approved'
        LIMIT 1
        """,
        (case_id, approval_type),
    ).fetchone()
    return row is not None


def _create_notification(
    conn: sqlite3.Connection,
    case_id: str | None,
    event_type: str,
    recipient: str | None,
    title: str,
    body: str,
    *,
    payload: Mapping[str, Any] | None = None,
    severity: str | None = None,
    channel: str = "in_app",
    status: str = "queued",
) -> dict[str, Any]:
    notification_id = _record_id("NTF", case_id or "system", event_type, recipient or "broadcast")
    conn.execute(
        """
        INSERT INTO notifications
            (notification_id, case_id, event_type, recipient, channel, severity, title, body,
             status, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notification_id,
            case_id,
            event_type,
            recipient,
            channel,
            severity,
            title,
            body,
            status,
            json.dumps(payload or {}, ensure_ascii=False),
            utc_now_iso(),
        ),
    )
    row = conn.execute("SELECT * FROM notifications WHERE notification_id = ?", (notification_id,)).fetchone()
    return dict(row)


def _upsert_operational_case(conn: sqlite3.Connection, signal: Mapping[str, Any]) -> tuple[str, str]:
    signal_key = str(signal["signal_key"])
    case_id = _case_id_from_signal(signal_key)
    now = utc_now_iso()
    severity = _normalize_case_severity(str(signal.get("severity", "medium")))
    existing = conn.execute(
        "SELECT * FROM operational_cases WHERE signal_key = ?",
        (signal_key,),
    ).fetchone()
    evidence_json = json.dumps(signal.get("evidence", {}), ensure_ascii=False)
    if existing is None:
        conn.execute(
            """
            INSERT INTO operational_cases
                (case_id, signal_key, title, severity, status, owner, line_id, station_id,
                 machine_id, source_type, signal_score, condition_score, first_seen_at,
                 last_seen_at, due_at, next_action, evidence_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                signal_key,
                str(signal.get("title", "Operational signal")),
                severity,
                "new",
                str(signal.get("owner", "unassigned")),
                signal.get("line_id"),
                signal.get("station_id"),
                signal.get("machine_id"),
                str(signal.get("source_type", "sensor-derived")),
                signal.get("signal_score"),
                signal.get("condition_score"),
                signal.get("first_seen_at") or signal.get("last_seen_at") or now,
                signal.get("last_seen_at") or now,
                signal.get("due_at") or _due_at_for_severity(signal.get("last_seen_at"), severity),
                str(signal.get("next_action", "Triage signal and confirm operating context.")),
                evidence_json,
                now,
                now,
            ),
        )
        _insert_case_event(conn, case_id, "created", note=str(signal.get("title", "Operational signal")), to_status="new", payload=signal)
        return case_id, "created"

    old = dict(existing)
    old_status = _normalize_case_status(old.get("status"))
    preserved_status = old_status if old_status in {"assigned", "investigating", "mitigated", "resolved"} else old_status
    conn.execute(
        """
        UPDATE operational_cases
        SET title = ?,
            severity = ?,
            status = ?,
            line_id = ?,
            station_id = ?,
            machine_id = ?,
            source_type = ?,
            signal_score = ?,
            condition_score = ?,
            last_seen_at = ?,
            due_at = COALESCE(due_at, ?),
            next_action = CASE WHEN next_action IS NULL OR next_action = '' THEN ? ELSE next_action END,
            evidence_json = ?,
            updated_at = ?
        WHERE signal_key = ?
        """,
        (
            str(signal.get("title", old.get("title", "Operational signal"))),
            severity,
            preserved_status,
            signal.get("line_id"),
            signal.get("station_id"),
            signal.get("machine_id"),
            str(signal.get("source_type", old.get("source_type", "sensor-derived"))),
            signal.get("signal_score"),
            signal.get("condition_score"),
            signal.get("last_seen_at") or old.get("last_seen_at") or now,
            signal.get("due_at") or _due_at_for_severity(signal.get("last_seen_at"), severity),
            str(signal.get("next_action", "Triage signal and confirm operating context.")),
            evidence_json,
            now,
            signal_key,
        ),
    )
    if _severity_rank(severity) > _severity_rank(old.get("severity")):
        _insert_case_event(
            conn,
            case_id,
            "severity_changed",
            note=f"Severity changed from {old.get('severity')} to {severity}",
            payload={"previous": old.get("severity"), "current": severity},
        )
    return case_id, "updated"


def _signals_from_alerts(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM anomaly_alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    signals = []
    for row in rows:
        item = dict(row)
        severity = _normalize_case_severity(item.get("severity"))
        machine = item.get("machine_id") or "unknown-machine"
        title = item.get("message") or f"Anomaly alert on {machine}"
        signals.append(
            {
                "signal_key": f"alert:{item.get('id')}",
                "title": str(title),
                "severity": severity,
                "machine_id": item.get("machine_id"),
                "line_id": item.get("line_id"),
                "station_id": item.get("station_id"),
                "source_type": item.get("source") or "model_alert",
                "signal_score": item.get("anomaly_score"),
                "last_seen_at": item.get("timestamp") or item.get("created_at"),
                "next_action": "Confirm alert, inspect recent trend, and assign owner.",
                "evidence": item,
            }
        )
    return signals


def _signals_from_predictions(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM predictions
        WHERE risk_level IN ('high', 'critical')
           OR COALESCE(anomaly_flag, 0) = 1
           OR COALESCE(failure_probability, 0) >= 0.55
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    signals = []
    for row in rows:
        item = dict(row)
        severity = _normalize_case_severity(item.get("risk_level"))
        machine = item.get("machine_id") or "unknown-machine"
        score = max(_as_float(item.get("failure_probability")), _as_float(item.get("anomaly_score")))
        signals.append(
            {
                "signal_key": f"prediction:{item.get('id')}",
                "title": f"Prediction risk on {machine}",
                "severity": severity,
                "machine_id": item.get("machine_id"),
                "line_id": item.get("line_id"),
                "station_id": item.get("station_id"),
                "source_type": "model_prediction",
                "signal_score": score,
                "condition_score": item.get("health_score"),
                "last_seen_at": item.get("timestamp") or item.get("created_at"),
                "next_action": item.get("recommended_action") or "Review prediction evidence and assign investigation.",
                "evidence": item,
            }
        )
    return signals


def _signals_from_data_quality(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM data_quality_issues
        WHERE severity IN ('high', 'critical')
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    signals = []
    for row in rows:
        item = dict(row)
        entity = item.get("entity_id") or item.get("machine_id") or item.get("station_id") or "data stream"
        signals.append(
            {
                "signal_key": f"quality:{item.get('id')}",
                "title": f"Data quality issue on {entity}",
                "severity": _normalize_case_severity(item.get("severity")),
                "machine_id": item.get("machine_id"),
                "line_id": item.get("line_id"),
                "station_id": item.get("station_id"),
                "source_type": "data_quality",
                "last_seen_at": item.get("timestamp") or item.get("detected_at"),
                "next_action": "Validate data channel before using analytics for decisions.",
                "evidence": item,
            }
        )
    return signals


def _signals_from_sensor_stream(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM sensor_readings
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (max(limit * 80, limit),),
    ).fetchall()
    strongest_by_machine: dict[str, dict[str, Any]] = {}
    signals = []
    for row in rows:
        item = dict(row)
        condition_score = _derive_condition_score(item)
        anomaly_index = round(_clamp(100.0 - condition_score) / 100.0, 3)
        severity = _severity_from_condition(condition_score, anomaly_index)
        if severity == "low":
            continue
        machine = item.get("machine_id") or "unknown-machine"
        current = strongest_by_machine.get(str(machine))
        if current and _as_float(current["anomaly_index"]) >= anomaly_index:
            continue
        strongest_by_machine[str(machine)] = {
            "item": item,
            "condition_score": condition_score,
            "anomaly_index": anomaly_index,
            "severity": severity,
        }
    for machine, candidate in sorted(
        strongest_by_machine.items(),
        key=lambda entry: _as_float(entry[1]["signal_score"] if "signal_score" in entry[1] else entry[1]["anomaly_index"]),
        reverse=True,
    )[:limit]:
        item = candidate["item"]
        condition_score = candidate["condition_score"]
        anomaly_index = candidate["anomaly_index"]
        severity = candidate["severity"]
        driver = _dominant_signal(item)
        signals.append(
            {
                "signal_key": f"derived_sensor:{machine}",
                "title": f"Recent {driver.replace('_', ' ').title()} signal on {machine}",
                "severity": severity,
                "machine_id": item.get("machine_id"),
                "line_id": item.get("line_id"),
                "station_id": item.get("station_id"),
                "source_type": "sensor-derived",
                "signal_score": anomaly_index,
                "condition_score": condition_score,
                "last_seen_at": item.get("timestamp") or item.get("created_at"),
                "next_action": "Review signal drivers, compare production context, and assign owner.",
                "evidence": {
                    "driver": driver,
                    "anomaly_index": anomaly_index,
                    "condition_score": condition_score,
                    "sensor_record_id": item.get("id"),
                    "vibration_rms": item.get("vibration_rms"),
                    "process_temperature": item.get("process_temperature"),
                    "motor_current": item.get("motor_current"),
                    "torque": item.get("torque"),
                    "tool_wear": item.get("tool_wear"),
                },
            }
        )
    return signals


def sync_operational_cases_from_signals(db_path: str | Path | None = None, limit: int = 50) -> dict[str, Any]:
    """Create or update workflow cases from alerts, predictions, quality issues, and sensor evidence."""
    initialize_database(db_path)
    created = 0
    updated = 0
    with connect(db_path) as conn:
        signals = (
            _signals_from_alerts(conn, limit)
            + _signals_from_predictions(conn, limit)
            + _signals_from_data_quality(conn, limit)
            + _signals_from_sensor_stream(conn, limit)
        )
        for signal in signals:
            _, action = _upsert_operational_case(conn, signal)
            if action == "created":
                created += 1
            else:
                updated += 1
        open_count = conn.execute(
            "SELECT COUNT(*) FROM operational_cases WHERE status != 'resolved'"
        ).fetchone()[0]
        conn.commit()
    return {"created": created, "updated": updated, "open_cases": int(open_count), "signals_seen": len(signals)}


def list_operational_cases(
    db_path: str | Path | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return recent operations workflow cases."""
    initialize_database(db_path)
    query = "SELECT * FROM operational_cases"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(_normalize_case_status(status))
    query += """
        ORDER BY
            CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,
            datetime(last_seen_at) DESC
        LIMIT ?
    """
    params.append(int(limit))
    with connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def list_operational_case_events(
    case_id: str,
    db_path: str | Path | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return audit events for one operations workflow case."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM operational_case_events
            WHERE case_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (case_id, int(limit)),
        ).fetchall()
    return [dict(row) for row in rows]


def update_operational_case(
    case_id: str,
    updates: Mapping[str, Any],
    db_path: str | Path | None = None,
    actor: str = "operator",
    note: str | None = None,
) -> dict[str, Any]:
    """Update case assignment/status fields and write an audit event."""
    initialize_database(db_path)
    allowed = {"status", "owner", "next_action", "due_at"}
    clean = {key: value for key, value in updates.items() if key in allowed and value is not None}
    if "status" in clean:
        clean["status"] = _normalize_case_status(str(clean["status"]))
    if not clean and not note:
        raise ValueError("No case update was provided.")

    with connect(db_path) as conn:
        current = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (case_id,)).fetchone()
        if current is None:
            raise KeyError(case_id)
        old = dict(current)
        if clean.get("status") == "resolved" and _severity_rank(old.get("severity")) >= 3:
            if not _case_has_approved_approval(conn, case_id, "resolve_case"):
                raise PermissionError("approval is required before resolving high-severity workflow cases")
        if clean:
            assignments = ", ".join([f"{key} = ?" for key in clean])
            values = list(clean.values())
            values.extend([utc_now_iso(), case_id])
            conn.execute(
                f"UPDATE operational_cases SET {assignments}, updated_at = ? WHERE case_id = ?",
                values,
            )
        _insert_case_event(
            conn,
            case_id,
            "case_updated",
            actor=actor,
            note=note,
            from_status=old.get("status"),
            to_status=str(clean.get("status", old.get("status"))),
            payload=clean,
        )
        if clean:
            _create_notification(
                conn,
                case_id,
                "case_updated",
                recipient=str(clean.get("owner") or old.get("owner") or "operator"),
                title=f"Case {case_id} updated",
                body=str(note or "Workflow case was updated."),
                payload={"updates": clean, "actor": actor},
                severity=str(old.get("severity") or "medium"),
            )
        updated = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (case_id,)).fetchone()
        conn.commit()
    return dict(updated)


def add_operational_case_event(
    case_id: str,
    event_type: str,
    note: str | None = None,
    actor: str = "operator",
    payload: Mapping[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append an audit event to an existing workflow case."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        current = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (case_id,)).fetchone()
        if current is None:
            raise KeyError(case_id)
        _insert_case_event(
            conn,
            case_id,
            event_type or "note",
            actor=actor,
            note=note,
            from_status=dict(current).get("status"),
            to_status=dict(current).get("status"),
            payload=payload,
        )
        event = conn.execute(
            "SELECT * FROM operational_case_events WHERE case_id = ? ORDER BY id DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        conn.commit()
    return dict(event)


def assign_case_owner(
    case_id: str,
    user_id: str,
    ownership_role: str,
    db_path: str | Path | None = None,
    assigned_by: str = "system",
) -> dict[str, Any]:
    """Assign a named workflow owner and notify the assignee."""
    initialize_database(db_path)
    clean_role = str(ownership_role or "primary").strip().lower()
    with connect(db_path) as conn:
        case = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (case_id,)).fetchone()
        if case is None:
            raise KeyError(case_id)
        _require_user_role(conn, user_id, "operator")
        if assigned_by != "system":
            _require_user_role(conn, assigned_by, "operator")
        now = utc_now_iso()
        conn.execute(
            """
            UPDATE case_ownership
            SET active = 0, released_at = ?
            WHERE case_id = ? AND ownership_role = ? AND active = 1
            """,
            (now, case_id, clean_role),
        )
        conn.execute(
            """
            INSERT INTO case_ownership
                (case_id, user_id, ownership_role, active, assigned_by, assigned_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (case_id, user_id, clean_role, assigned_by, now),
        )
        if clean_role == "primary":
            conn.execute(
                "UPDATE operational_cases SET owner = ?, status = CASE WHEN status = 'new' THEN 'assigned' ELSE status END, updated_at = ? WHERE case_id = ?",
                (user_id, now, case_id),
            )
        _insert_case_event(
            conn,
            case_id,
            "owner_assigned",
            actor=assigned_by,
            note=f"{user_id} assigned as {clean_role} owner",
            from_status=dict(case).get("status"),
            to_status="assigned" if clean_role == "primary" and dict(case).get("status") == "new" else dict(case).get("status"),
            payload={"user_id": user_id, "ownership_role": clean_role},
        )
        _create_notification(
            conn,
            case_id,
            "owner_assigned",
            recipient=user_id,
            title=f"Case {case_id} assigned",
            body=f"You are the {clean_role} owner for this workflow case.",
            payload={"assigned_by": assigned_by, "ownership_role": clean_role},
            severity=dict(case).get("severity"),
        )
        row = conn.execute(
            "SELECT * FROM case_ownership WHERE case_id = ? AND user_id = ? AND ownership_role = ? ORDER BY id DESC LIMIT 1",
            (case_id, user_id, clean_role),
        ).fetchone()
        conn.commit()
    return dict(row)


def list_case_owners(case_id: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return active and historical owners for one case."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM case_ownership
            WHERE case_id = ?
            ORDER BY active DESC, datetime(assigned_at) DESC, id DESC
            """,
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def request_case_approval(
    case_id: str,
    approval_type: str,
    requested_by: str,
    db_path: str | Path | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a pending approval record for a governed workflow action."""
    initialize_database(db_path)
    clean_type = str(approval_type or "workflow_action").strip().lower()
    with connect(db_path) as conn:
        case = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (case_id,)).fetchone()
        if case is None:
            raise KeyError(case_id)
        _require_user_role(conn, requested_by, "operator")
        approval_id = _record_id("APR", case_id, clean_type, requested_by)
        conn.execute(
            """
            INSERT INTO case_approvals
                (approval_id, case_id, approval_type, requested_by, status, reason,
                 policy_version, requested_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (approval_id, case_id, clean_type, requested_by, reason, "operations-policy-v1", utc_now_iso()),
        )
        _insert_case_event(
            conn,
            case_id,
            "approval_requested",
            actor=requested_by,
            note=reason,
            from_status=dict(case).get("status"),
            to_status=dict(case).get("status"),
            payload={"approval_id": approval_id, "approval_type": clean_type},
        )
        _create_notification(
            conn,
            case_id,
            "approval_requested",
            recipient="supervisor",
            title=f"Approval requested for {case_id}",
            body=reason or f"{clean_type} requires supervisor decision.",
            payload={"approval_id": approval_id, "approval_type": clean_type, "requested_by": requested_by},
            severity=dict(case).get("severity"),
        )
        row = conn.execute("SELECT * FROM case_approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        conn.commit()
    return dict(row)


def decide_case_approval(
    approval_id: str,
    decision: str,
    decided_by: str,
    db_path: str | Path | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Approve or reject a pending workflow approval."""
    initialize_database(db_path)
    clean_decision = str(decision or "").strip().lower()
    if clean_decision not in {"approved", "rejected"}:
        raise ValueError("Approval decision must be approved or rejected.")
    with connect(db_path) as conn:
        _require_user_role(conn, decided_by, "supervisor")
        approval = conn.execute("SELECT * FROM case_approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        if approval is None:
            raise KeyError(approval_id)
        approval_dict = dict(approval)
        now = utc_now_iso()
        conn.execute(
            """
            UPDATE case_approvals
            SET status = ?, decided_by = ?, decision_note = ?, decided_at = ?
            WHERE approval_id = ?
            """,
            (clean_decision, decided_by, note, now, approval_id),
        )
        case = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (approval_dict["case_id"],)).fetchone()
        case_status = dict(case).get("status") if case else None
        _insert_case_event(
            conn,
            approval_dict["case_id"],
            "approval_decided",
            actor=decided_by,
            note=note,
            from_status=case_status,
            to_status=case_status,
            payload={"approval_id": approval_id, "decision": clean_decision},
        )
        _create_notification(
            conn,
            approval_dict["case_id"],
            "approval_decided",
            recipient=approval_dict.get("requested_by"),
            title=f"Approval {clean_decision}",
            body=note or f"{approval_dict.get('approval_type')} was {clean_decision}.",
            payload={"approval_id": approval_id, "decision": clean_decision, "decided_by": decided_by},
            severity=dict(case).get("severity") if case else None,
        )
        row = conn.execute("SELECT * FROM case_approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        conn.commit()
    return dict(row)


def list_case_approvals(db_path: str | Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return recent workflow approvals."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM case_approvals
            ORDER BY datetime(requested_at) DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def dispatch_case_to_external(
    case_id: str,
    target_system: str,
    requested_by: str,
    db_path: str | Path | None = None,
    endpoint_url: str | None = None,
) -> dict[str, Any]:
    """Queue a governed handoff for an external CMMS/MES-style connector."""
    initialize_database(db_path)
    clean_target = str(target_system or "").strip().lower()
    if clean_target not in {"cmms", "mes"}:
        raise ValueError("target_system must be cmms or mes")
    with connect(db_path) as conn:
        _require_user_role(conn, requested_by, "supervisor")
        case = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (case_id,)).fetchone()
        if case is None:
            raise KeyError(case_id)
        case_dict = dict(case)
        work_order_id = _record_id("WO", case_id, clean_target)
        now = utc_now_iso()
        task_summary = f"{case_dict.get('title', 'Workflow case')} [{case_id}]"
        conn.execute(
            """
            INSERT INTO work_orders
                (work_order_id, case_id, status, owner, task_summary, external_ref, created_at, updated_at)
            VALUES (?, ?, 'queued', ?, ?, ?, ?, ?)
            """,
            (work_order_id, case_id, requested_by, task_summary, None, now, now),
        )
        payload = {
            "case_id": case_id,
            "work_order_id": work_order_id,
            "target_system": clean_target,
            "title": case_dict.get("title"),
            "severity": case_dict.get("severity"),
            "machine_id": case_dict.get("machine_id"),
            "line_id": case_dict.get("line_id"),
            "station_id": case_dict.get("station_id"),
            "requested_by": requested_by,
        }
        conn.execute(
            """
            INSERT INTO integration_outbox
                (connector_type, target_system, case_id, work_order_id, status, endpoint_url,
                 payload_json, attempts, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'queued', ?, ?, 0, ?, ?)
            """,
            (
                f"{clean_target}_connector",
                clean_target,
                case_id,
                work_order_id,
                endpoint_url,
                json.dumps(payload, ensure_ascii=False),
                now,
                now,
            ),
        )
        _insert_case_event(
            conn,
            case_id,
            "external_dispatch_queued",
            actor=requested_by,
            note=f"Queued handoff to {clean_target.upper()}",
            from_status=case_dict.get("status"),
            to_status=case_dict.get("status"),
            payload=payload,
        )
        _create_notification(
            conn,
            case_id,
            "external_dispatch_queued",
            recipient=requested_by,
            title=f"{clean_target.upper()} handoff queued",
            body=f"Work order {work_order_id} is queued in the integration outbox.",
            payload=payload,
            severity=case_dict.get("severity"),
        )
        row = conn.execute(
            "SELECT * FROM integration_outbox WHERE case_id = ? AND work_order_id = ? ORDER BY outbox_id DESC LIMIT 1",
            (case_id, work_order_id),
        ).fetchone()
        conn.commit()
    result = dict(row)
    return {
        "case_id": case_id,
        "work_order_id": work_order_id,
        "target_system": clean_target,
        "outbox_status": result["status"],
        "outbox_id": result["outbox_id"],
    }


def list_integration_outbox(db_path: str | Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return queued and recent external connector handoffs."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM integration_outbox
            ORDER BY datetime(created_at) DESC, outbox_id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def list_dispatchable_integration_outbox(
    db_path: str | Path | None = None,
    target_system: str | None = None,
    limit: int = 20,
    max_attempts: int = 3,
) -> list[dict[str, Any]]:
    """Return connector outbox rows that can be attempted by the dispatcher."""
    initialize_database(db_path)
    params: list[Any] = [int(max_attempts)]
    query = """
        SELECT *
        FROM integration_outbox
        WHERE status IN ('queued', 'retrying', 'not_configured')
          AND COALESCE(attempts, 0) < ?
    """
    if target_system:
        query += " AND target_system = ?"
        params.append(str(target_system).lower())
    query += " ORDER BY datetime(created_at) ASC, outbox_id ASC LIMIT ?"
    params.append(int(limit))
    with connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def record_integration_outbox_result(
    outbox_id: int,
    status: str,
    db_path: str | Path | None = None,
    response_status: int | None = None,
    response_body: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Persist one connector dispatch attempt and append the workflow audit trail."""
    initialize_database(db_path)
    clean_status = str(status or "").strip().lower()
    if clean_status not in {"sent", "failed", "retrying", "dead_letter", "not_configured"}:
        raise ValueError("Unsupported connector dispatch status.")
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM integration_outbox WHERE outbox_id = ?", (int(outbox_id),)).fetchone()
        if row is None:
            raise KeyError(outbox_id)
        item = dict(row)
        now = utc_now_iso()
        attempts_increment = 0 if clean_status == "not_configured" else 1
        conn.execute(
            """
            UPDATE integration_outbox
            SET status = ?,
                response_status = ?,
                response_body = ?,
                attempts = COALESCE(attempts, 0) + ?,
                updated_at = ?,
                sent_at = CASE WHEN ? = 'sent' THEN ? ELSE sent_at END
            WHERE outbox_id = ?
            """,
            (
                clean_status,
                response_status,
                response_body or error_message,
                attempts_increment,
                now,
                clean_status,
                now,
                int(outbox_id),
            ),
        )
        work_order_status = {
            "sent": "sent",
            "failed": "failed",
            "retrying": "retrying",
            "dead_letter": "dead_letter",
            "not_configured": "not_configured",
        }[clean_status]
        conn.execute(
            "UPDATE work_orders SET status = ?, updated_at = ? WHERE work_order_id = ?",
            (work_order_status, now, item.get("work_order_id")),
        )
        event_type = {
            "sent": "external_dispatch_sent",
            "failed": "external_dispatch_failed",
            "retrying": "external_dispatch_retrying",
            "dead_letter": "external_dispatch_failed",
            "not_configured": "external_dispatch_not_configured",
        }[clean_status]
        note = {
            "sent": f"{str(item.get('target_system')).upper()} handoff accepted.",
            "failed": f"{str(item.get('target_system')).upper()} handoff failed.",
            "retrying": f"{str(item.get('target_system')).upper()} handoff will retry.",
            "dead_letter": f"{str(item.get('target_system')).upper()} handoff moved to dead letter.",
            "not_configured": f"{str(item.get('target_system')).upper()} endpoint is not configured.",
        }[clean_status]
        case = conn.execute("SELECT * FROM operational_cases WHERE case_id = ?", (item.get("case_id"),)).fetchone()
        case_status = dict(case).get("status") if case else None
        payload = {
            "outbox_id": int(outbox_id),
            "work_order_id": item.get("work_order_id"),
            "target_system": item.get("target_system"),
            "status": clean_status,
            "response_status": response_status,
            "response_body": response_body,
            "error_message": error_message,
        }
        _insert_case_event(
            conn,
            str(item.get("case_id")),
            event_type,
            actor="connector-dispatcher",
            note=note,
            from_status=case_status,
            to_status=case_status,
            payload=payload,
        )
        _create_notification(
            conn,
            str(item.get("case_id")),
            event_type,
            recipient="supervisor",
            title=note,
            body=response_body or error_message or note,
            payload=payload,
            severity=dict(case).get("severity") if case else None,
        )
        updated = conn.execute("SELECT * FROM integration_outbox WHERE outbox_id = ?", (int(outbox_id),)).fetchone()
        conn.commit()
    return dict(updated)


def integration_outbox_status_counts(db_path: str | Path | None = None) -> dict[str, dict[str, int]]:
    """Return outbox status counts grouped by target system."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT target_system, status, COUNT(*) AS count
            FROM integration_outbox
            GROUP BY target_system, status
            """
        ).fetchall()
    result: dict[str, dict[str, int]] = {}
    for row in rows:
        target = str(row["target_system"] or "unknown")
        result.setdefault(target, {})[str(row["status"])] = int(row["count"])
    return result


def list_notifications(db_path: str | Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return recent workflow notifications."""
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM notifications
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


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
        "integration_outbox",
        "notifications",
        "case_approvals",
        "case_ownership",
        "operational_case_events",
        "work_orders",
        "operational_cases",
        "reports",
        "system_logs",
        "data_acquisition_logs",
    ]
    with connect(db_path) as conn:
        for table in synthetic_tables + (core_tables if include_core else []):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
