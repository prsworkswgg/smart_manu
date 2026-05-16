"""Data validation rules for sensor and production data.

The functions in this module return structured quality issues instead of raising
exceptions.  This makes the data quality engine usable in production-like
pipelines where bad rows should be logged, not crash the entire pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd


@dataclass
class QualityIssue:
    """A normalized data quality issue ready to insert into SQLite."""

    issue_type: str
    severity: str
    entity_type: str
    entity_id: str | None = None
    machine_id: str | None = None
    line_id: str | None = None
    station_id: str | None = None
    timestamp: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self) -> dict[str, Any]:
        """Convert the issue to a dictionary matching data_quality_issues."""
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "machine_id": self.machine_id,
            "line_id": self.line_id,
            "station_id": self.station_id,
            "timestamp": self.timestamp,
            "details_json": json.dumps(self.details, ensure_ascii=False),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }


SENSOR_REQUIRED_COLUMNS = [
    "machine_id",
    "line_id",
    "station_id",
    "timestamp",
    "air_temperature",
    "process_temperature",
    "vibration_rms",
    "vibration_peak",
    "pressure",
    "torque",
    "rotational_speed",
    "motor_current",
    "power_consumption",
    "tool_wear",
    "operating_hours",
    "production_load",
    "ambient_humidity",
]

PRODUCTION_REQUIRED_COLUMNS = [
    "line_id",
    "station_id",
    "batch_id",
    "shift",
    "timestamp",
    "cycle_time_sec",
    "throughput_count",
    "target_throughput",
    "station_yield",
    "reject_count",
    "rework_count",
    "defect_rate",
    "micro_stop_count",
    "downtime_minutes",
    "wip_count",
    "queue_length",
    "inspection_score_proxy",
    "process_stability_index",
    "operator_group",
]


def ensure_datetime(df: pd.DataFrame, column: str = "timestamp") -> pd.DataFrame:
    """Return a copy with the timestamp column converted to timezone-aware datetime."""
    out = df.copy()
    if column in out.columns:
        out[column] = pd.to_datetime(out[column], errors="coerce", utc=True)
    return out


def _row_identity(row: pd.Series) -> dict[str, Any]:
    """Extract common identifiers from a row."""
    return {
        "entity_id": str(row.get("id")) if pd.notna(row.get("id")) else None,
        "machine_id": str(row.get("machine_id")) if pd.notna(row.get("machine_id")) else None,
        "line_id": str(row.get("line_id")) if pd.notna(row.get("line_id")) else None,
        "station_id": str(row.get("station_id")) if pd.notna(row.get("station_id")) else None,
        "timestamp": row.get("timestamp").isoformat() if hasattr(row.get("timestamp"), "isoformat") else str(row.get("timestamp")) if pd.notna(row.get("timestamp")) else None,
    }


def detect_missing_required_columns(
    df: pd.DataFrame,
    required_columns: Iterable[str],
    entity_type: str,
) -> list[QualityIssue]:
    """Detect missing columns in an input table."""
    issues: list[QualityIssue] = []
    missing = [col for col in required_columns if col not in df.columns]
    for col in missing:
        issues.append(
            QualityIssue(
                issue_type="missing_required_column",
                severity="critical",
                entity_type=entity_type,
                details={"column": col},
            )
        )
    return issues


def detect_missing_values(
    df: pd.DataFrame,
    required_columns: Iterable[str],
    entity_type: str,
) -> list[QualityIssue]:
    """Detect null values in required data columns."""
    issues: list[QualityIssue] = []
    present_cols = [c for c in required_columns if c in df.columns]
    for idx, row in df.iterrows():
        missing_cols = [col for col in present_cols if pd.isna(row.get(col))]
        if not missing_cols:
            continue
        identity = _row_identity(row)
        issues.append(
            QualityIssue(
                issue_type="missing_value",
                severity="high",
                entity_type=entity_type,
                **identity,
                details={"row_index": int(idx), "missing_columns": missing_cols},
            )
        )
    return issues


def detect_duplicate_timestamps(
    df: pd.DataFrame,
    group_columns: list[str],
    entity_type: str,
) -> list[QualityIssue]:
    """Detect duplicate timestamps within a machine/station or line/station group."""
    issues: list[QualityIssue] = []
    if "timestamp" not in df.columns:
        return issues

    subset = [c for c in group_columns + ["timestamp"] if c in df.columns]
    if len(subset) < 2:
        return issues

    duplicated = df[df.duplicated(subset=subset, keep=False)].copy()
    for _, row in duplicated.iterrows():
        identity = _row_identity(row)
        issues.append(
            QualityIssue(
                issue_type="duplicate_timestamp",
                severity="medium",
                entity_type=entity_type,
                **identity,
                details={"duplicate_key": {col: str(row.get(col)) for col in subset}},
            )
        )
    return issues


def detect_timestamp_gaps(
    df: pd.DataFrame,
    group_columns: list[str],
    entity_type: str,
    expected_interval_seconds: int = 300,
    gap_multiplier: int = 6,
) -> list[QualityIssue]:
    """Detect large gaps in timestamp sequences per group."""
    issues: list[QualityIssue] = []
    if df.empty or "timestamp" not in df.columns:
        return issues

    threshold = pd.Timedelta(seconds=expected_interval_seconds * gap_multiplier)
    sorted_df = ensure_datetime(df).sort_values(group_columns + ["timestamp"])

    for group_key, group in sorted_df.groupby(group_columns, dropna=False):
        deltas = group["timestamp"].diff()
        gap_rows = group[deltas > threshold]
        for idx, row in gap_rows.iterrows():
            identity = _row_identity(row)
            issues.append(
                QualityIssue(
                    issue_type="timestamp_gap",
                    severity="medium",
                    entity_type=entity_type,
                    **identity,
                    details={
                        "group_columns": group_columns,
                        "group_key": str(group_key),
                        "gap_seconds": float(deltas.loc[idx].total_seconds()),
                        "threshold_seconds": float(threshold.total_seconds()),
                    },
                )
            )
    return issues


def detect_impossible_sensor_values(df: pd.DataFrame) -> list[QualityIssue]:
    """Detect physically impossible or schema-invalid sensor values."""
    issues: list[QualityIssue] = []
    checks = {
        "vibration_rms": lambda s: s < 0,
        "vibration_peak": lambda s: s < 0,
        "pressure": lambda s: s < 0,
        "torque": lambda s: s < 0,
        "rotational_speed": lambda s: s < 0,
        "motor_current": lambda s: s < 0,
        "power_consumption": lambda s: s < 0,
        "tool_wear": lambda s: (s < 0) | (s > 100),
        "operating_hours": lambda s: s < 0,
        "production_load": lambda s: s < 0,
        "ambient_humidity": lambda s: (s < 0) | (s > 100),
    }
    for col, rule in checks.items():
        if col not in df.columns:
            continue
        bad = df[rule(pd.to_numeric(df[col], errors="coerce"))]
        for _, row in bad.iterrows():
            identity = _row_identity(row)
            issues.append(
                QualityIssue(
                    issue_type="impossible_value",
                    severity="high",
                    entity_type="sensor_reading",
                    **identity,
                    details={"column": col, "value": row.get(col)},
                )
            )
    return issues


def detect_impossible_production_values(df: pd.DataFrame) -> list[QualityIssue]:
    """Detect impossible production values such as yield > 1 or negative counts."""
    issues: list[QualityIssue] = []
    checks = {
        "station_yield": lambda s: (s < 0) | (s > 1),
        "defect_rate": lambda s: (s < 0) | (s > 1),
        "inspection_score_proxy": lambda s: (s < 0) | (s > 1),
        "process_stability_index": lambda s: (s < 0) | (s > 1),
        "cycle_time_sec": lambda s: s <= 0,
        "throughput_count": lambda s: s < 0,
        "target_throughput": lambda s: s < 0,
        "reject_count": lambda s: s < 0,
        "rework_count": lambda s: s < 0,
        "micro_stop_count": lambda s: s < 0,
        "downtime_minutes": lambda s: s < 0,
        "wip_count": lambda s: s < 0,
        "queue_length": lambda s: s < 0,
    }
    for col, rule in checks.items():
        if col not in df.columns:
            continue
        bad = df[rule(pd.to_numeric(df[col], errors="coerce"))]
        for _, row in bad.iterrows():
            identity = _row_identity(row)
            issues.append(
                QualityIssue(
                    issue_type="impossible_value",
                    severity="high",
                    entity_type="production_event",
                    **identity,
                    details={"column": col, "value": row.get(col)},
                )
            )
    return issues


def detect_stuck_sensor(
    df: pd.DataFrame,
    sensor_columns: list[str] | None = None,
    min_run_length: int = 6,
) -> list[QualityIssue]:
    """Detect flatline/stuck sensors using historical repeated values per machine/station."""
    issues: list[QualityIssue] = []
    if df.empty:
        return issues

    sensor_columns = sensor_columns or [
        "air_temperature",
        "process_temperature",
        "vibration_rms",
        "pressure",
        "torque",
        "motor_current",
        "power_consumption",
    ]
    available = [c for c in sensor_columns if c in df.columns]
    sorted_df = ensure_datetime(df).sort_values(["machine_id", "station_id", "timestamp"])

    for (machine_id, station_id), group in sorted_df.groupby(["machine_id", "station_id"], dropna=False):
        for col in available:
            series = pd.to_numeric(group[col], errors="coerce")
            same_as_previous = series.diff().abs().fillna(999.0) < 1e-9
            run_id = (same_as_previous != same_as_previous.shift()).cumsum()
            run_lengths = same_as_previous.groupby(run_id).transform("sum") + 1
            stuck_rows = group[(same_as_previous) & (run_lengths >= min_run_length)]
            if stuck_rows.empty:
                continue
            last = stuck_rows.iloc[-1]
            identity = _row_identity(last)
            issues.append(
                QualityIssue(
                    issue_type="stuck_sensor",
                    severity="high",
                    entity_type="sensor_reading",
                    **identity,
                    details={
                        "machine_id": str(machine_id),
                        "station_id": str(station_id),
                        "column": col,
                        "min_run_length": min_run_length,
                        "example_value": last.get(col),
                    },
                )
            )
    return issues


def detect_sensor_dropout(df: pd.DataFrame, min_missing_sensor_columns: int = 5) -> list[QualityIssue]:
    """Detect rows that look like sensor dropouts because many sensor values are null."""
    issues: list[QualityIssue] = []
    sensor_columns = [
        "air_temperature",
        "process_temperature",
        "vibration_rms",
        "vibration_peak",
        "pressure",
        "torque",
        "rotational_speed",
        "motor_current",
        "power_consumption",
    ]
    present = [c for c in sensor_columns if c in df.columns]
    if not present:
        return issues

    missing_counts = df[present].isna().sum(axis=1)
    dropout_rows = df[missing_counts >= min_missing_sensor_columns]
    for idx, row in dropout_rows.iterrows():
        identity = _row_identity(row)
        issues.append(
            QualityIssue(
                issue_type="sensor_dropout",
                severity="high",
                entity_type="sensor_reading",
                **identity,
                details={
                    "row_index": int(idx),
                    "missing_sensor_columns": int(missing_counts.loc[idx]),
                    "threshold": min_missing_sensor_columns,
                },
            )
        )
    return issues


def detect_delayed_readings(
    df: pd.DataFrame,
    entity_type: str,
    max_delay_seconds: int = 60,
) -> list[QualityIssue]:
    """Detect delayed readings using created_at - timestamp when created_at is available."""
    issues: list[QualityIssue] = []
    if "timestamp" not in df.columns or "created_at" not in df.columns:
        return issues

    tmp = df.copy()
    tmp["timestamp"] = pd.to_datetime(tmp["timestamp"], errors="coerce", utc=True)
    tmp["created_at"] = pd.to_datetime(tmp["created_at"], errors="coerce", utc=True)
    delay_seconds = (tmp["created_at"] - tmp["timestamp"]).dt.total_seconds()
    delayed = tmp[delay_seconds > max_delay_seconds]
    for idx, row in delayed.iterrows():
        identity = _row_identity(row)
        issues.append(
            QualityIssue(
                issue_type="delayed_reading",
                severity="medium",
                entity_type=entity_type,
                **identity,
                details={
                    "delay_seconds": float(delay_seconds.loc[idx]),
                    "threshold_seconds": max_delay_seconds,
                },
            )
        )
    return issues


def validate_sensor_readings(df: pd.DataFrame) -> list[QualityIssue]:
    """Run all sensor-reading validation rules."""
    if df.empty:
        return [
            QualityIssue(
                issue_type="empty_table",
                severity="medium",
                entity_type="sensor_reading",
                details={"message": "sensor_readings table is empty"},
            )
        ]
    df = ensure_datetime(df)
    issues: list[QualityIssue] = []
    issues += detect_missing_required_columns(df, SENSOR_REQUIRED_COLUMNS, "sensor_reading")
    issues += detect_missing_values(df, SENSOR_REQUIRED_COLUMNS, "sensor_reading")
    issues += detect_duplicate_timestamps(df, ["machine_id", "station_id"], "sensor_reading")
    issues += detect_timestamp_gaps(df, ["machine_id", "station_id"], "sensor_reading")
    issues += detect_impossible_sensor_values(df)
    issues += detect_stuck_sensor(df)
    issues += detect_sensor_dropout(df)
    issues += detect_delayed_readings(df, "sensor_reading")
    return issues


def validate_production_events(df: pd.DataFrame) -> list[QualityIssue]:
    """Run all production-event validation rules."""
    if df.empty:
        return [
            QualityIssue(
                issue_type="empty_table",
                severity="medium",
                entity_type="production_event",
                details={"message": "production_events table is empty"},
            )
        ]
    df = ensure_datetime(df)
    issues: list[QualityIssue] = []
    issues += detect_missing_required_columns(df, PRODUCTION_REQUIRED_COLUMNS, "production_event")
    issues += detect_missing_values(df, PRODUCTION_REQUIRED_COLUMNS, "production_event")
    issues += detect_duplicate_timestamps(df, ["line_id", "station_id"], "production_event")
    issues += detect_timestamp_gaps(df, ["line_id", "station_id"], "production_event")
    issues += detect_impossible_production_values(df)
    issues += detect_delayed_readings(df, "production_event")
    return issues
