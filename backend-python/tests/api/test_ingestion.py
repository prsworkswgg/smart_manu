from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(temp_db):
    from api.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_valid_sensor_reading_is_accepted(temp_db, sample_sensor_payload):
    from api.main import app
    client = TestClient(app)
    response = client.post("/ingest/sensor-reading", json=sample_sensor_payload)
    assert response.status_code == 200
    assert response.json()["table"] == "sensor_readings"


def test_valid_production_event_is_accepted(temp_db, sample_production_payload):
    from api.main import app
    client = TestClient(app)
    response = client.post("/ingest/production-event", json=sample_production_payload)
    assert response.status_code == 200
    assert response.json()["table"] == "production_events"


def test_invalid_payload_is_rejected(temp_db):
    from api.main import app
    client = TestClient(app)
    response = client.post("/ingest/sensor-reading", json={"bad": "payload"})
    assert response.status_code == 422


def test_missing_machine_id_is_rejected(temp_db, sample_sensor_payload):
    from api.main import app
    client = TestClient(app)
    payload = dict(sample_sensor_payload)
    payload.pop("machine_id")
    response = client.post("/ingest/sensor-reading", json=payload)
    assert response.status_code == 422


def test_malformed_timestamp_is_rejected(temp_db, sample_sensor_payload):
    from api.main import app
    client = TestClient(app)
    payload = dict(sample_sensor_payload)
    payload["timestamp"] = "not-a-date"
    response = client.post("/ingest/sensor-reading", json=payload)
    assert response.status_code == 422


def test_duplicate_event_id_does_not_duplicate_records(temp_db, sample_sensor_payload):
    from api.main import app
    from database import repository
    client = TestClient(app)
    assert client.post("/ingest/sensor-reading", json=sample_sensor_payload).status_code == 200
    assert client.post("/ingest/sensor-reading", json=sample_sensor_payload).status_code == 200
    df = repository.read_sensor_readings(temp_db)
    assert len(df[df["event_id"] == sample_sensor_payload["event_id"]]) == 1
