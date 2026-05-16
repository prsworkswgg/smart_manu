from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend-python" / "src"
BACKEND = ROOT / "backend-python"
for path in [str(SRC), str(BACKEND), str(ROOT)]:
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db = tmp_path / "test_smop.db"
    monkeypatch.setenv("SMOP_DB_PATH", str(db))
    monkeypatch.setenv("DATABASE_PATH", str(db))
    from database import repository
    repository.initialize_database(db)
    return db


@pytest.fixture()
def sample_sensor_payload():
    return {
        "event_id": "SENSOR_TEST_001",
        "machine_id": "MTR_TEST_01",
        "line_id": "LINE_TEST",
        "station_id": "ST_TEST_01",
        "timestamp": "2026-05-01T06:00:00Z",
        "air_temperature": 28.0,
        "process_temperature": 58.0,
        "vibration_rms": 1.5,
        "vibration_peak": 4.5,
        "pressure": 115.0,
        "torque": 25.0,
        "rotational_speed": 1800.0,
        "motor_current": 7.5,
        "power_consumption": 3.2,
        "tool_wear": 35.0,
        "operating_hours": 1200.0,
        "production_load": 0.9,
        "ambient_humidity": 55.0,
    }


@pytest.fixture()
def sample_production_payload():
    return {
        "event_id": "PROD_TEST_001",
        "line_id": "LINE_TEST",
        "station_id": "ST_TEST_01",
        "batch_id": "LOT_TEST_001",
        "shift": "DAY",
        "timestamp": "2026-05-01T06:00:00Z",
        "cycle_time_sec": 6.0,
        "throughput_count": 10,
        "target_throughput": 12,
        "station_yield": 0.97,
        "reject_count": 1,
        "rework_count": 0,
        "defect_rate": 0.03,
        "micro_stop_count": 1,
        "downtime_minutes": 0.2,
        "wip_count": 30,
        "queue_length": 8,
        "inspection_score_proxy": 0.95,
        "process_stability_index": 0.88,
        "operator_group": "DAY",
    }
