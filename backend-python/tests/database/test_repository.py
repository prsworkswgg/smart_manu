from __future__ import annotations

import sqlite3


def test_database_tables_are_created(temp_db):
    with sqlite3.connect(temp_db) as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "sensor_readings" in names
    assert "production_events" in names
    assert "synthetic_machine_sensor_readings" in names


def test_sensor_records_insert_and_read(temp_db, sample_sensor_payload):
    from database import repository
    row_id = repository.insert_sensor_reading(sample_sensor_payload, temp_db)
    df = repository.read_sensor_readings(temp_db)
    assert row_id >= 0
    assert len(df) == 1
    assert df.iloc[0]["machine_id"] == "MTR_TEST_01"


def test_production_records_insert_and_read(temp_db, sample_production_payload):
    from database import repository
    row_id = repository.insert_production_event(sample_production_payload, temp_db)
    df = repository.read_production_events(temp_db)
    assert row_id >= 0
    assert len(df) == 1
    assert df.iloc[0]["line_id"] == "LINE_TEST"


def test_empty_database_status_does_not_crash(temp_db):
    from database import repository
    status = repository.get_data_acquisition_status(temp_db)
    assert status["sensor_readings"] == 0
    assert status["production_events"] == 0


def test_expected_columns_exist(temp_db):
    import sqlite3
    with sqlite3.connect(temp_db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(sensor_readings)")}
    assert {"event_id", "machine_id", "timestamp", "vibration_rms"}.issubset(cols)
