from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_preprocessing_handles_empty_database(temp_db, tmp_path):
    from data.preprocessing import run_preprocessing
    out = tmp_path / "processed.csv"
    summary = run_preprocessing(db_path=temp_db, output_path=out)
    assert out.exists()
    assert summary["processed_rows"] == 0


def test_timestamp_join_does_not_use_future_data(temp_db, sample_sensor_payload, sample_production_payload):
    from database import repository
    from features.join_sensor_production import join_sensor_production
    past_sensor = dict(sample_sensor_payload)
    past_sensor["timestamp"] = "2026-05-01T06:00:00Z"
    future_sensor = dict(sample_sensor_payload)
    future_sensor["event_id"] = "SENSOR_FUTURE"
    future_sensor["timestamp"] = "2026-05-01T06:10:00Z"
    future_sensor["vibration_rms"] = 99.0
    prod = dict(sample_production_payload)
    prod["timestamp"] = "2026-05-01T06:05:00Z"
    repository.insert_sensor_reading(past_sensor, temp_db)
    repository.insert_sensor_reading(future_sensor, temp_db)
    repository.insert_production_event(prod, temp_db)
    joined = join_sensor_production(repository.read_sensor_readings(temp_db), repository.read_production_events(temp_db), tolerance="30min")
    assert len(joined) == 1
    assert joined.iloc[0]["vibration_rms"] != 99.0


def test_impossible_values_generate_quality_issues(temp_db, sample_sensor_payload):
    from database import repository
    from data.data_quality import run_data_quality_checks
    bad = dict(sample_sensor_payload)
    bad["vibration_rms"] = -1.0
    repository.insert_sensor_reading(bad, temp_db)
    summary = run_data_quality_checks(temp_db)
    assert summary["issue_count"] >= 1


def test_duplicate_records_detected(temp_db, sample_sensor_payload):
    from database import repository
    from data.data_quality import run_data_quality_checks
    a = dict(sample_sensor_payload)
    b = dict(sample_sensor_payload)
    b["event_id"] = "SENSOR_TEST_002"
    repository.insert_sensor_reading(a, temp_db)
    repository.insert_sensor_reading(b, temp_db)
    summary = run_data_quality_checks(temp_db)
    assert summary["issue_type_counts"].get("duplicate_timestamp", 0) >= 1
