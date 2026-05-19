from __future__ import annotations

import sqlite3


def test_database_tables_are_created(temp_db):
    with sqlite3.connect(temp_db) as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "sensor_readings" in names
    assert "production_events" in names
    assert "synthetic_machine_sensor_readings" in names
    assert "operational_cases" in names
    assert "operational_case_events" in names
    assert "work_orders" in names


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


def test_sync_operational_cases_from_sensor_signal(temp_db, sample_sensor_payload):
    from database import repository

    risky = dict(sample_sensor_payload)
    risky["event_id"] = "SENSOR_RISK_001"
    risky["machine_id"] = "MTR_RISK_01"
    risky["process_temperature"] = 88.0
    risky["vibration_rms"] = 3.2
    risky["tool_wear"] = 82.0
    repository.insert_sensor_reading(risky, temp_db)

    result = repository.sync_operational_cases_from_signals(temp_db)
    cases = repository.list_operational_cases(temp_db)

    assert result["created"] == 1
    assert len(cases) == 1
    assert cases[0]["machine_id"] == "MTR_RISK_01"
    assert cases[0]["status"] == "new"
    assert cases[0]["source_type"] == "sensor-derived"


def test_update_operational_case_writes_event(temp_db, sample_sensor_payload):
    from database import repository

    risky = dict(sample_sensor_payload)
    risky["event_id"] = "SENSOR_RISK_002"
    risky["machine_id"] = "MTR_RISK_02"
    risky["process_temperature"] = 90.0
    risky["vibration_rms"] = 3.4
    risky["tool_wear"] = 90.0
    repository.insert_sensor_reading(risky, temp_db)
    repository.sync_operational_cases_from_signals(temp_db)
    case = repository.list_operational_cases(temp_db)[0]

    updated = repository.update_operational_case(
        case["case_id"],
        {"status": "assigned", "owner": "shift-lead"},
        temp_db,
        actor="test",
        note="Assign for inspection",
    )
    events = repository.list_operational_case_events(case["case_id"], temp_db)

    assert updated["status"] == "assigned"
    assert updated["owner"] == "shift-lead"
    assert any(event["event_type"] == "case_updated" for event in events)


def test_api_key_authenticates_seeded_enterprise_users(temp_db):
    from database import repository

    viewer = repository.authenticate_api_key("demo-viewer-key", temp_db)
    operator = repository.authenticate_api_key("demo-operator-key", temp_db)
    supervisor = repository.authenticate_api_key("demo-supervisor-key", temp_db)

    assert viewer["role"] == "viewer"
    assert operator["role"] == "operator"
    assert supervisor["role"] == "supervisor"
    assert repository.user_has_role(operator, "viewer") is True
    assert repository.user_has_role(viewer, "operator") is False


def test_case_assignment_creates_multi_owner_record_and_notification(temp_db, sample_sensor_payload):
    from database import repository

    risky = dict(sample_sensor_payload)
    risky["event_id"] = "SENSOR_OWNER_001"
    risky["machine_id"] = "MTR_OWNER_01"
    risky["process_temperature"] = 88.0
    risky["vibration_rms"] = 3.2
    risky["tool_wear"] = 82.0
    repository.insert_sensor_reading(risky, temp_db)
    repository.sync_operational_cases_from_signals(temp_db)
    case = repository.list_operational_cases(temp_db)[0]

    repository.assign_case_owner(case["case_id"], "operator", "primary", temp_db, assigned_by="supervisor")
    owners = repository.list_case_owners(case["case_id"], temp_db)
    notifications = repository.list_notifications(temp_db)

    assert owners[0]["user_id"] == "operator"
    assert owners[0]["ownership_role"] == "primary"
    assert any(note["case_id"] == case["case_id"] for note in notifications)


def test_high_case_requires_approval_before_resolved(temp_db, sample_sensor_payload):
    from database import repository

    risky = dict(sample_sensor_payload)
    risky["event_id"] = "SENSOR_APPROVAL_001"
    risky["machine_id"] = "MTR_APPROVAL_01"
    risky["process_temperature"] = 96.0
    risky["vibration_rms"] = 4.4
    risky["tool_wear"] = 95.0
    repository.insert_sensor_reading(risky, temp_db)
    repository.sync_operational_cases_from_signals(temp_db)
    case = repository.list_operational_cases(temp_db)[0]
    assert case["severity"] in {"high", "critical"}

    try:
        repository.update_operational_case(case["case_id"], {"status": "resolved"}, temp_db, actor="operator")
    except PermissionError as exc:
        assert "approval" in str(exc)
    else:
        raise AssertionError("Resolving a high-severity case without approval must fail")

    approval = repository.request_case_approval(case["case_id"], "resolve_case", "operator", temp_db, reason="Signal cleared")
    decided = repository.decide_case_approval(approval["approval_id"], "approved", "supervisor", temp_db, note="Reviewed evidence")
    updated = repository.update_operational_case(case["case_id"], {"status": "resolved"}, temp_db, actor="operator")

    assert decided["status"] == "approved"
    assert updated["status"] == "resolved"


def test_external_dispatch_creates_work_order_outbox_and_notification(temp_db, sample_sensor_payload):
    from database import repository

    risky = dict(sample_sensor_payload)
    risky["event_id"] = "SENSOR_DISPATCH_001"
    risky["machine_id"] = "MTR_DISPATCH_01"
    risky["process_temperature"] = 90.0
    risky["vibration_rms"] = 3.3
    risky["tool_wear"] = 85.0
    repository.insert_sensor_reading(risky, temp_db)
    repository.sync_operational_cases_from_signals(temp_db)
    case = repository.list_operational_cases(temp_db)[0]

    dispatch = repository.dispatch_case_to_external(case["case_id"], "cmms", "supervisor", temp_db)
    outbox = repository.list_integration_outbox(temp_db)
    notifications = repository.list_notifications(temp_db)

    assert dispatch["outbox_status"] == "queued"
    assert dispatch["work_order_id"].startswith("WO-")
    assert outbox[0]["target_system"] == "cmms"
    assert any(note["event_type"] == "external_dispatch_queued" for note in notifications)
