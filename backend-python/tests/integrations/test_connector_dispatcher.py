from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _ReceiverHandler(BaseHTTPRequestHandler):
    received: list[dict] = []
    status_code = 201

    def do_POST(self):  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        self.__class__.received.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "json": json.loads(body),
            }
        )
        self.send_response(self.__class__.status_code)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"external_ref":"CMMS-ACCEPTED"}')

    def log_message(self, *_args):
        return


def _start_receiver(status_code: int = 201):
    _ReceiverHandler.received = []
    _ReceiverHandler.status_code = status_code
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ReceiverHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, _ReceiverHandler.received


def _queue_cmms_handoff(temp_db, sample_sensor_payload):
    from database import repository

    risky = dict(sample_sensor_payload)
    risky["event_id"] = "SENSOR_CONNECTOR_001"
    risky["machine_id"] = "MTR_CONNECTOR_01"
    risky["process_temperature"] = 90.0
    risky["vibration_rms"] = 3.3
    risky["tool_wear"] = 85.0
    repository.insert_sensor_reading(risky, temp_db)
    repository.sync_operational_cases_from_signals(temp_db)
    case = repository.list_operational_cases(temp_db)[0]
    return repository.dispatch_case_to_external(case["case_id"], "cmms", "supervisor", temp_db)


def test_connector_dispatcher_posts_queued_outbox_to_configured_endpoint(temp_db, sample_sensor_payload, monkeypatch):
    from database import repository
    from integrations.connector_dispatcher import dispatch_queued_handoffs

    receiver, received = _start_receiver(status_code=201)
    try:
        queued = _queue_cmms_handoff(temp_db, sample_sensor_payload)
        monkeypatch.setenv("SMOP_CMMS_ENDPOINT", f"http://127.0.0.1:{receiver.server_port}/work-orders")
        monkeypatch.setenv("SMOP_CMMS_TOKEN", "connector-token")

        result = dispatch_queued_handoffs(temp_db, target_system="cmms")
        outbox = repository.list_integration_outbox(temp_db)
        notifications = repository.list_notifications(temp_db)

        assert result["sent"] == 1
        assert result["failed"] == 0
        assert outbox[0]["status"] == "sent"
        assert outbox[0]["response_status"] == 201
        assert outbox[0]["attempts"] == 1
        assert received[0]["path"] == "/work-orders"
        assert received[0]["headers"]["Authorization"] == "Bearer connector-token"
        assert received[0]["headers"]["Idempotency-Key"] == queued["work_order_id"]
        assert received[0]["json"]["case_id"] == queued["case_id"]
        assert received[0]["json"]["work_order_id"] == queued["work_order_id"]
        assert any(note["event_type"] == "external_dispatch_sent" for note in notifications)
    finally:
        receiver.shutdown()


def test_connector_dispatcher_marks_outbox_not_configured_when_endpoint_missing(temp_db, sample_sensor_payload, monkeypatch):
    from database import repository
    from integrations.connector_dispatcher import dispatch_queued_handoffs

    _queue_cmms_handoff(temp_db, sample_sensor_payload)
    monkeypatch.delenv("SMOP_CMMS_ENDPOINT", raising=False)
    monkeypatch.delenv("SMOP_CMMS_TOKEN", raising=False)

    result = dispatch_queued_handoffs(temp_db, target_system="cmms")
    outbox = repository.list_integration_outbox(temp_db)
    notifications = repository.list_notifications(temp_db)

    assert result["not_configured"] == 1
    assert outbox[0]["status"] == "not_configured"
    assert any(note["event_type"] == "external_dispatch_not_configured" for note in notifications)


def test_connector_dispatcher_retries_server_errors(temp_db, sample_sensor_payload, monkeypatch):
    from database import repository
    from integrations.connector_dispatcher import dispatch_queued_handoffs

    receiver, _received = _start_receiver(status_code=503)
    try:
        _queue_cmms_handoff(temp_db, sample_sensor_payload)
        monkeypatch.setenv("SMOP_CMMS_ENDPOINT", f"http://127.0.0.1:{receiver.server_port}/work-orders")

        result = dispatch_queued_handoffs(temp_db, target_system="cmms", max_attempts=3)
        outbox = repository.list_integration_outbox(temp_db)

        assert result["retrying"] == 1
        assert outbox[0]["status"] == "retrying"
        assert outbox[0]["response_status"] == 503
        assert outbox[0]["attempts"] == 1
    finally:
        receiver.shutdown()
