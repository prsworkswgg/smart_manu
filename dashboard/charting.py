"""Chart preparation helpers for Streamlit dashboard pages."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ChartWindow:
    """User-facing time window configuration."""

    label: str
    hours: int | None


WINDOW_OPTIONS = (
    ChartWindow("Latest 1 hour", 1),
    ChartWindow("Latest 6 hours", 6),
    ChartWindow("Latest 24 hours", 24),
    ChartWindow("All data", None),
)


def chart_window_options(lang: str = "en") -> list[str]:
    """Return localized chart window labels."""
    if lang == "th":
        return ["1 ชั่วโมงล่าสุด", "6 ชั่วโมงล่าสุด", "24 ชั่วโมงล่าสุด", "ข้อมูลทั้งหมด"]
    if lang == "zh":
        return ["最近 1 小时", "最近 6 小时", "最近 24 小时", "全部数据"]
    if lang == "ja":
        return ["直近 1 時間", "直近 6 時間", "直近 24 時間", "すべて"]
    return [item.label for item in WINDOW_OPTIONS]


def hours_from_window_label(label: str) -> int | None:
    """Map localized labels back to hour windows."""
    if "1" in label:
        return 1
    if "6" in label:
        return 6
    if "24" in label:
        return 24
    return None


def filter_time_window(df: pd.DataFrame, timestamp_col: str = "timestamp", hours: int | None = 24) -> pd.DataFrame:
    """Filter a data frame to the latest time window based on its own max timestamp."""
    if df.empty or hours is None or timestamp_col not in df.columns:
        return df.copy()
    out = df.copy()
    out[timestamp_col] = pd.to_datetime(out[timestamp_col], errors="coerce", utc=True)
    valid_ts = out[timestamp_col].dropna()
    if valid_ts.empty:
        return out
    cutoff = valid_ts.max() - pd.Timedelta(hours=hours)
    return out[out[timestamp_col] >= cutoff].copy()


def downsample_timeseries(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    group_col: str | None = None,
    max_points: int = 900,
) -> pd.DataFrame:
    """Downsample large time series while keeping first/last records."""
    if df.empty or len(df) <= max_points:
        return df.copy()
    out = df.sort_values(timestamp_col).copy() if timestamp_col in df.columns else df.copy()
    if group_col and group_col in out.columns:
        pieces: list[pd.DataFrame] = []
        groups = max(1, out[group_col].nunique())
        budget = max(12, max_points // groups)
        for _, group_df in out.groupby(group_col, dropna=False):
            pieces.append(_downsample_single(group_df, budget))
        return pd.concat(pieces, ignore_index=True).sort_values(timestamp_col) if timestamp_col in out.columns else pd.concat(pieces, ignore_index=True)
    return _downsample_single(out, max_points)


def prepare_timeseries(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    group_col: str | None = None,
    hours: int | None = 24,
    max_points: int = 900,
) -> pd.DataFrame:
    """Filter and downsample a time series for readable dashboard charts."""
    windowed = filter_time_window(df, timestamp_col=timestamp_col, hours=hours)
    return downsample_timeseries(windowed, timestamp_col=timestamp_col, group_col=group_col, max_points=max_points)


def _downsample_single(df: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if len(df) <= max_points:
        return df.copy()
    stride = max(1, len(df) // max_points)
    sampled = df.iloc[::stride].copy()
    tail = df.tail(1)
    if sampled.empty or not sampled.tail(1).equals(tail):
        sampled = pd.concat([sampled, tail]).drop_duplicates()
    return sampled
