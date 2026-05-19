"""Dispatch governed CMMS/MES handoffs from the local integration outbox."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from database import repository


@dataclass(frozen=True)
class ConnectorConfig:
    target_system: str
    endpoint: str | None
    auth_type: str
    token: str | None
    timeout_seconds: float

    @property
    def configured(self) -> bool:
        return bool(self.endpoint)


def connector_config(target_system: str, endpoint_override: str | None = None) -> ConnectorConfig:
    """Build connector configuration from env variables and an optional row-level endpoint."""
    target = str(target_system or "").strip().lower()
    env_prefix = f"SMOP_{target.upper()}"
    timeout = float(os.environ.get(f"{env_prefix}_TIMEOUT_SECONDS", "10"))
    return ConnectorConfig(
        target_system=target,
        endpoint=endpoint_override or os.environ.get(f"{env_prefix}_ENDPOINT"),
        auth_type=os.environ.get(f"{env_prefix}_AUTH_TYPE", "bearer").strip().lower(),
        token=os.environ.get(f"{env_prefix}_TOKEN"),
        timeout_seconds=timeout,
    )


def _headers(config: ConnectorConfig, work_order_id: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": work_order_id,
        "X-SMOP-Connector": config.target_system,
    }
    if config.token:
        if config.auth_type == "api-key":
            headers["X-API-Key"] = config.token
        else:
            headers["Authorization"] = f"Bearer {config.token}"
    return headers


def _payload(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get("payload_json") or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"payload_text": raw}
    payload.setdefault("case_id", item.get("case_id"))
    payload.setdefault("work_order_id", item.get("work_order_id"))
    payload.setdefault("target_system", item.get("target_system"))
    return payload


def _status_for_response(status_code: int, attempts_after_call: int, max_attempts: int) -> str:
    if 200 <= status_code < 300:
        return "sent"
    if 400 <= status_code < 500:
        return "failed"
    return "retrying" if attempts_after_call < max_attempts else "dead_letter"


def dispatch_queued_handoffs(
    db_path: str | Path | None = None,
    target_system: str | None = None,
    limit: int = 20,
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Send queued integration outbox records to configured external endpoints."""
    summary: dict[str, Any] = {
        "attempted": 0,
        "sent": 0,
        "failed": 0,
        "retrying": 0,
        "dead_letter": 0,
        "not_configured": 0,
        "items": [],
    }
    items = repository.list_dispatchable_integration_outbox(
        db_path,
        target_system=target_system,
        limit=limit,
        max_attempts=max_attempts,
    )
    for item in items:
        config = connector_config(str(item.get("target_system")), endpoint_override=item.get("endpoint_url"))
        if not config.configured:
            updated = repository.record_integration_outbox_result(
                int(item["outbox_id"]),
                "not_configured",
                db_path,
                error_message=f"{str(item.get('target_system')).upper()} endpoint is not configured.",
            )
            summary["not_configured"] += 1
            summary["items"].append(updated)
            continue

        summary["attempted"] += 1
        attempts_after_call = int(item.get("attempts") or 0) + 1
        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(
                    str(config.endpoint),
                    headers=_headers(config, str(item.get("work_order_id"))),
                    json=_payload(item),
                )
            status = _status_for_response(response.status_code, attempts_after_call, max_attempts)
            updated = repository.record_integration_outbox_result(
                int(item["outbox_id"]),
                status,
                db_path,
                response_status=response.status_code,
                response_body=response.text[:2000],
            )
        except httpx.HTTPError as exc:
            status = "retrying" if attempts_after_call < max_attempts else "dead_letter"
            updated = repository.record_integration_outbox_result(
                int(item["outbox_id"]),
                status,
                db_path,
                error_message=str(exc),
            )

        if status in {"sent", "failed", "retrying", "dead_letter"}:
            summary[status] += 1
        summary["items"].append(updated)
    return summary


def connector_status(db_path: str | Path | None = None) -> dict[str, Any]:
    """Return connector readiness and outbox state for dashboard/API display."""
    counts = repository.integration_outbox_status_counts(db_path)
    status: dict[str, Any] = {}
    for target in ["cmms", "mes"]:
        config = connector_config(target)
        target_counts = counts.get(target, {})
        status[target] = {
            "configured": config.configured,
            "endpoint": config.endpoint,
            "queued": target_counts.get("queued", 0),
            "sent": target_counts.get("sent", 0),
            "retrying": target_counts.get("retrying", 0),
            "failed": target_counts.get("failed", 0),
            "dead_letter": target_counts.get("dead_letter", 0),
            "not_configured": target_counts.get("not_configured", 0),
        }
    return status
