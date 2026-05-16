-- SQLite schema for Smart Manufacturing AI Operations Platform.
-- Simulated-data working prototype only. No real Seagate or proprietary factory data.

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
CREATE INDEX IF NOT EXISTS idx_sensor_station_ts ON sensor_readings(machine_id, station_id, timestamp);

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
CREATE INDEX IF NOT EXISTS idx_production_station_ts ON production_events(line_id, station_id, timestamp);

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

CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT,
    component TEXT,
    message TEXT,
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

-- Operational indexes and views used by the production-style dashboard.
CREATE INDEX IF NOT EXISTS idx_predictions_machine_ts ON predictions(machine_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_line_risk_ts ON predictions(line_id, risk_level, timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_severity_ts ON anomaly_alerts(severity, timestamp);
CREATE INDEX IF NOT EXISTS idx_quality_severity_detected ON data_quality_issues(severity, detected_at);

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
