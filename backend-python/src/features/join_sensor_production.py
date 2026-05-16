"""Time-safe joining of sensor readings and production events.

The join uses ``pd.merge_asof`` with ``direction='backward'`` so each
production event receives the latest sensor reading at or before the production
timestamp.  This avoids using future sensor data for a past production event.
"""

from __future__ import annotations

import pandas as pd


def _to_utc_timestamp(df: pd.DataFrame, column: str = "timestamp") -> pd.DataFrame:
    out = df.copy()
    out[column] = pd.to_datetime(out[column], errors="coerce", utc=True)
    return out


def join_sensor_production(
    sensor_df: pd.DataFrame,
    production_df: pd.DataFrame,
    tolerance: str | pd.Timedelta = "5min",
) -> pd.DataFrame:
    """Join production events to latest historical sensor readings by line/station.

    Parameters
    ----------
    sensor_df:
        DataFrame from ``sensor_readings``.
    production_df:
        DataFrame from ``production_events``.
    tolerance:
        Maximum time lag allowed between production event and sensor reading.

    Returns
    -------
    pd.DataFrame
        Joined dataset, one row per production event when a matching historical
        sensor reading is found.
    """
    if sensor_df.empty or production_df.empty:
        return pd.DataFrame()

    sensor = _to_utc_timestamp(sensor_df)
    production = _to_utc_timestamp(production_df)

    required_sensor = {"line_id", "station_id", "timestamp"}
    required_production = {"line_id", "station_id", "timestamp"}
    missing_sensor = required_sensor - set(sensor.columns)
    missing_production = required_production - set(production.columns)
    if missing_sensor:
        raise ValueError(f"sensor_df missing columns: {sorted(missing_sensor)}")
    if missing_production:
        raise ValueError(f"production_df missing columns: {sorted(missing_production)}")

    sensor = sensor.dropna(subset=["line_id", "station_id", "timestamp"]).copy()
    production = production.dropna(subset=["line_id", "station_id", "timestamp"]).copy()
    sensor["sensor_timestamp"] = sensor["timestamp"]
    production["event_timestamp"] = production["timestamp"]

    joined_parts: list[pd.DataFrame] = []
    tolerance_td = pd.Timedelta(tolerance)

    for (line_id, station_id), prod_group in production.groupby(["line_id", "station_id"], dropna=False):
        sensor_group = sensor[(sensor["line_id"] == line_id) & (sensor["station_id"] == station_id)].copy()
        if sensor_group.empty:
            continue

        prod_group = prod_group.sort_values("timestamp").reset_index(drop=True)
        sensor_group = sensor_group.sort_values("timestamp").reset_index(drop=True)

        merged = pd.merge_asof(
            prod_group,
            sensor_group,
            on="timestamp",
            by=["line_id", "station_id"],
            direction="backward",
            tolerance=tolerance_td,
            suffixes=("_prod", ""),
        )
        joined_parts.append(merged)

    if not joined_parts:
        return pd.DataFrame()

    joined = pd.concat(joined_parts, ignore_index=True)
    joined = joined.dropna(subset=["sensor_timestamp"]).copy()
    joined["join_lag_seconds"] = (joined["event_timestamp"] - joined["sensor_timestamp"]).dt.total_seconds()
    joined = joined.sort_values(["line_id", "station_id", "timestamp"]).reset_index(drop=True)
    return joined
