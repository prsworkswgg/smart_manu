"""Lightweight i18n audit helpers for dashboard labels."""

from __future__ import annotations

import re


ALLOWED_TECH_TERMS = {
    "API",
    "OT",
    "OT/IT",
    "IT",
    "PC",
    "C",
    "API",
    "CMMS",
    "CMMS/MES",
    "collector/API",
    "CSV",
    "DEMO",
    "Dashboard",
    "Edge",
    "FastAPI",
    "HTTP",
    "ID",
    "JSONL",
    "JSON",
    "Markdown",
    "MES",
    "ML",
    "MTTR",
    "OEE",
    "PLC",
    "RUL",
    "SensorCollector",
    "SQLite",
    "SMOP",
    "Streamlit",
    "acceptance",
    "action",
    "alert",
    "analytics",
    "anomaly",
    "approval",
    "artifact",
    "audit",
    "baseline",
    "case",
    "collector",
    "condition",
    "connector",
    "critical",
    "current",
    "cycle",
    "dashboard",
    "data",
    "dead",
    "downtime",
    "endpoint",
    "enterprise",
    "event",
    "factory",
    "feature",
    "flag",
    "hardcode",
    "health",
    "heartbeat",
    "high",
    "historian",
    "importance",
    "inference",
    "ingestion",
    "integration",
    "joblib",
    "label",
    "letter",
    "live",
    "log",
    "maintenance",
    "micro",
    "model",
    "motor",
    "notification",
    "outbox",
    "owner",
    "path",
    "pattern",
    "production",
    "quality",
    "record",
    "records",
    "registry",
    "review",
    "score",
    "security",
    "sensor",
    "station",
    "stop",
    "stream",
    "supervisor",
    "telemetry",
    "temperature",
    "testing",
    "time",
    "torque",
    "trend",
    "triage",
    "vibration",
    "wear",
    "workflow",
    "yield",
}

ASCII_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_/.-]*\b")


def english_tokens(text: str) -> list[str]:
    """Return English-looking tokens excluding accepted technical terms."""
    tokens = ASCII_WORD_RE.findall(text)
    return [
        token
        for token in tokens
        if token not in ALLOWED_TECH_TERMS
        and not token.startswith("MTR_")
        and not token.islower()  # lowercase placeholders such as {value}
    ]


def audit_language_strings(text_map: dict[str, dict[str, str]], lang: str = "th") -> list[tuple[str, list[str]]]:
    """Find localized strings that still contain unexpected English tokens."""
    findings: list[tuple[str, list[str]]] = []
    for key, value in sorted(text_map.get(lang, {}).items()):
        if not isinstance(value, str):
            continue
        tokens = english_tokens(value)
        if tokens:
            findings.append((key, tokens))
    return findings
