"""Feature engineering and leakage controls for machine learning.

All rolling features are computed after sorting by timestamp and use ``shift(1)``
before rolling.  That means historical rolling statistics do not use the current
or future row.

This project uses synthetic labels.  Feature columns are explicitly separated
from target, synthetic label, hidden-state, and operational baseline columns so
model metrics are not presented as proof of real factory accuracy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

TARGET_COLUMNS = [
    "failure_label",
    "rul_estimate_hours",
    "rul_target",
    "anomaly_label",
    "future_failure_window",
]

SYNTHETIC_LABEL_COLUMNS = [
    "failure_label",
    "rul_target",
    "rul_estimate_hours",
    "future_failure_window",
    "synthetic_failure_rule",
]

OPERATIONAL_CONTEXT_COLUMNS = [
    "site_id",
    "area_id",
    "line_id",
    "machine_id",
    "station_id",
    "timestamp",
    "event_timestamp",
    "sensor_timestamp",
    "shift",
    "load_state",
    "product_family",
    "recipe_id",
    "lot_id",
    "failure_mode",
    "operator_group",
]

EXCLUDED_LEAKAGE_COLUMNS = [
    "hidden_degradation_state",
    "equipment_process_risk_index",
    "synthetic_risk_index",
    "future_failure_window",
    "failure_label",
    "rul_target",
    "rul_estimate_hours",
    "anomaly_label",
    "defect_rate",
    "station_yield",
    "first_pass_yield",
    "inspection_score_proxy",
    "reject_count",
    "rework_count",
]

SENSOR_FEATURE_COLUMNS = [
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

PROCESS_STATE_FEATURE_COLUMNS = [
    "cycle_time_sec",
    "throughput_count",
    "target_throughput",
    "micro_stop_count",
    "downtime_minutes",
    "wip_count",
    "queue_length",
    "process_stability_index",
    "join_lag_seconds",
]

ENGINEERED_FEATURE_COLUMNS = [
    "temperature_delta",
    "vibration_severity_index",
    "torque_per_speed",
    "motor_load_index",
    "power_efficiency_index",
    "tool_wear_rate",
    "rolling_vibration_mean",
    "rolling_temperature_std",
    "cycle_time_drift",
    "throughput_gap",
    "micro_stop_rate",
    "downtime_ratio",
    "queue_pressure_index",
    "process_stability_trend",
]

# Operational baseline score is useful for dashboarding, but it is intentionally
# excluded from model training because synthetic labels may be generated from it.
OPERATIONAL_BASELINE_COLUMNS = ["equipment_process_risk_index"]

FEATURE_COLUMNS = SENSOR_FEATURE_COLUMNS + PROCESS_STATE_FEATURE_COLUMNS + ENGINEERED_FEATURE_COLUMNS
TRAINING_FEATURE_COLUMNS = FEATURE_COLUMNS

SUSPICIOUS_NAME_TOKENS = ["label", "target", "future", "failure", "rul", "hidden", "risk_index"]


def assert_no_leakage(feature_columns: Sequence[str]) -> None:
    """Raise ValueError when known target/leakage columns are present."""
    features = set(feature_columns)
    blocked = features.intersection(TARGET_COLUMNS + SYNTHETIC_LABEL_COLUMNS + EXCLUDED_LEAKAGE_COLUMNS)
    if blocked:
        raise ValueError(f"Leakage-risk columns found in feature list: {sorted(blocked)}")


def leakage_warnings(feature_columns: Sequence[str]) -> list[str]:
    """Return warnings for suspicious feature names that are not explicitly blocked."""
    warnings: list[str] = []
    for col in feature_columns:
        lowered = col.lower()
        if any(token in lowered for token in SUSPICIOUS_NAME_TOKENS):
            warnings.append(f"Suspicious feature name: {col}")
    return warnings


def ensure_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Convert selected columns to numeric, keeping missing values as NaN."""
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def historical_rolling_mean(df: pd.DataFrame, group_cols: list[str], column: str, window: int = 12) -> pd.Series:
    """Compute group-wise rolling mean using only rows before the current row."""
    return df.groupby(group_cols, dropna=False)[column].transform(
        lambda s: s.shift(1).rolling(window=window, min_periods=1).mean()
    )


def historical_rolling_std(df: pd.DataFrame, group_cols: list[str], column: str, window: int = 12) -> pd.Series:
    """Compute group-wise rolling std using only rows before the current row."""
    return df.groupby(group_cols, dropna=False)[column].transform(
        lambda s: s.shift(1).rolling(window=window, min_periods=2).std()
    )


def historical_diff_per_hour(df: pd.DataFrame, group_cols: list[str], value_col: str, timestamp_col: str = "timestamp") -> pd.Series:
    """Compute per-hour rate of change aligned to the original DataFrame index."""
    output = pd.Series(index=df.index, dtype=float)
    for _, group in df.groupby(group_cols, dropna=False):
        group = group.sort_values(timestamp_col)
        value_delta = group[value_col].diff()
        hours_delta = group[timestamp_col].diff().dt.total_seconds() / 3600.0
        rate = value_delta / hours_delta.replace(0, np.nan)
        output.loc[group.index] = rate.values
    return output.replace([np.inf, -np.inf], np.nan)


def add_engineered_features(joined_df: pd.DataFrame, rolling_window: int = 12) -> pd.DataFrame:
    """Create ML features and synthetic targets from joined sensor + production data.

    Synthetic targets are created after feature construction.  They are never
    included in ``FEATURE_COLUMNS``.  ``equipment_process_risk_index`` is kept as
    an operational baseline score, not a model training feature.
    """
    if joined_df.empty:
        return joined_df.copy()

    df = joined_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    sort_cols = [c for c in ["machine_id", "station_id", "timestamp"] if c in df.columns]
    df = df.sort_values(sort_cols).reset_index(drop=True)

    for col in SENSOR_FEATURE_COLUMNS + PROCESS_STATE_FEATURE_COLUMNS + ["defect_rate", "station_yield", "inspection_score_proxy", "reject_count", "rework_count"]:
        if col not in df.columns:
            df[col] = 0.0 if col not in {"station_yield", "inspection_score_proxy"} else 1.0
    df = ensure_numeric(df, SENSOR_FEATURE_COLUMNS + PROCESS_STATE_FEATURE_COLUMNS + ["defect_rate", "station_yield", "inspection_score_proxy", "reject_count", "rework_count"])
    eps = 1e-6

    df["temperature_delta"] = df["process_temperature"] - df["air_temperature"]
    df["vibration_severity_index"] = np.sqrt(
        df["vibration_rms"].fillna(0) ** 2 + (df["vibration_peak"].fillna(0) / 3.0) ** 2
    )
    df["torque_per_speed"] = df["torque"] / (df["rotational_speed"].abs() + eps)
    df["motor_load_index"] = (df["motor_current"] * df["torque"]) / (df["rotational_speed"].abs() + 1.0)
    df["power_efficiency_index"] = df["throughput_count"] / (df["power_consumption"].abs() + eps)

    group_machine = [c for c in ["machine_id", "station_id"] if c in df.columns] or ["station_id"]
    group_station = [c for c in ["line_id", "station_id"] if c in df.columns] or ["station_id"]

    df["tool_wear_rate"] = historical_diff_per_hour(df, group_machine, "tool_wear").fillna(0).clip(lower=0)
    df["rolling_vibration_mean"] = historical_rolling_mean(df, group_machine, "vibration_rms", rolling_window).fillna(df["vibration_rms"])
    df["rolling_temperature_std"] = historical_rolling_std(df, group_machine, "process_temperature", rolling_window).fillna(0)

    prev_cycle_mean = historical_rolling_mean(df, group_station, "cycle_time_sec", rolling_window).fillna(df["cycle_time_sec"])
    df["cycle_time_drift"] = df["cycle_time_sec"] - prev_cycle_mean

    prev_stability_mean = historical_rolling_mean(df, group_station, "process_stability_index", rolling_window).fillna(df["process_stability_index"])
    df["process_stability_trend"] = df["process_stability_index"] - prev_stability_mean

    df["throughput_gap"] = (df["target_throughput"] - df["throughput_count"]).fillna(0)
    df["micro_stop_rate"] = df["micro_stop_count"] / (df["throughput_count"].abs() + 1.0)
    runtime_minutes = (df["cycle_time_sec"] * df["throughput_count"]).clip(lower=1.0) / 60.0
    df["downtime_ratio"] = df["downtime_minutes"] / (runtime_minutes + eps)
    df["queue_pressure_index"] = df["queue_length"] / (df["wip_count"].abs() + df["throughput_count"].abs() + 1.0)

    tool_wear_index = (df["tool_wear"] / 100.0).clip(0, 1)
    vibration_index = (df["vibration_severity_index"] / 6.0).clip(0, 1)
    temperature_index = (df["temperature_delta"].abs() / 55.0).clip(0, 1)
    defect_index = (df["defect_rate"] / 0.15).clip(0, 1)
    stability_loss = (1.0 - df["process_stability_index"]).clip(0, 1)
    downtime_index = df["downtime_ratio"].clip(0, 1)
    df["equipment_process_risk_index"] = (
        0.24 * tool_wear_index
        + 0.24 * vibration_index
        + 0.13 * temperature_index
        + 0.17 * defect_index
        + 0.14 * stability_loss
        + 0.08 * downtime_index
    ).clip(0, 1)

    # Label creation can look ahead in synthetic data because labels are not
    # training features.  This models a future failure window while preserving a
    # time-aware feature set.
    if "failure_label" not in df.columns:
        future_risk = df.groupby(group_machine, dropna=False)["equipment_process_risk_index"].shift(-6)
        future_wear = df.groupby(group_machine, dropna=False)["tool_wear"].shift(-6)
        future_vibration = df.groupby(group_machine, dropna=False)["vibration_rms"].shift(-6)
        df["future_failure_window"] = ((future_risk >= 0.62) | ((future_wear >= 82) & (future_vibration >= 3.5))).fillna(False).astype(int)
        df["failure_label"] = df["future_failure_window"].astype(int)
    elif "future_failure_window" not in df.columns:
        df["future_failure_window"] = df["failure_label"].astype(int)

    if "rul_target" not in df.columns and "rul_estimate_hours" not in df.columns:
        wear_remaining = (100.0 - df["tool_wear"]).clip(lower=0)
        wear_rate = df["tool_wear_rate"].replace(0, np.nan)
        rate_based_rul = wear_remaining / wear_rate
        heuristic_rul = wear_remaining * 18.0
        df["rul_target"] = rate_based_rul.fillna(heuristic_rul).clip(lower=0, upper=5000)
        df["rul_estimate_hours"] = df["rul_target"]
    elif "rul_estimate_hours" not in df.columns and "rul_target" in df.columns:
        df["rul_estimate_hours"] = df["rul_target"]
    elif "rul_target" not in df.columns and "rul_estimate_hours" in df.columns:
        df["rul_target"] = df["rul_estimate_hours"]

    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    assert_no_leakage(FEATURE_COLUMNS)
    return df


def save_processed_dataset(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Save processed ML dataset as CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
