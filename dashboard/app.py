"""Streamlit dashboard for the Smart Manufacturing AI Operations Platform.

The dashboard reads operational data from SQLite. It does not use hardcoded demo
values. Empty tables are handled with clear fallback messages so the app can be
opened before data collection, training, or prediction has run.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import os
from html import escape
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import streamlit as st
except Exception:  # pragma: no cover - allows data-helper tests without Streamlit installed
    class _NoOpCache:
        def __call__(self, ttl: int | None = None):
            def decorator(func):
                func.clear = lambda: None
                return func
            return decorator

    class _StreamlitShim:
        cache_data = _NoOpCache()

        def __getattr__(self, name):
            def _noop(*args, **kwargs):
                if name in {"warning", "info", "caption", "success", "error"} and args:
                    print(args[0])
                return None
            return _noop

    st = _StreamlitShim()

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - fallback for minimal environments
    px = None
    go = None


APP_TITLE = "Smart Manufacturing AI Operations Platform"
DISCLAIMER = (
    "Simulated-data working prototype. No real Seagate data, no proprietary "
    "factory data, and no real factory deployment are claimed."
)

SYSTEM_PROFILE = {
    "site": "SMOP Demo Fab",
    "area": "Precision Electronics Line",
    "mode": "Simulated factory replay",
    "owner": "Manufacturing AI / Operations",
}

PAGE_ICONS = {
    "Executive Overview": "📊",
    "Data Acquisition Status": "📡",
    "Line Monitoring": "🏭",
    "Equipment Health": "🩺",
    "Process Anomaly": "🚨",
    "Data Quality": "🧪",
    "Model Training & Registry": "🧠",
    "Reports / Edge Deployment": "📄",
}


def inject_global_style() -> None:
    """Apply a production-style visual system to the Streamlit dashboard."""
    st.markdown(
        """
<style>
:root {
    --smop-bg: #0f172a;
    --smop-panel: #ffffff;
    --smop-muted: #64748b;
    --smop-border: #e2e8f0;
    --smop-info: #2563eb;
    --smop-ok: #047857;
    --smop-warn: #b45309;
    --smop-risk: #b91c1c;
}
.block-container {
    padding-top: 1.15rem;
    padding-bottom: 2.5rem;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
}
[data-testid="stSidebar"] * {
    color: #e5e7eb;
}
[data-testid="stSidebar"] .stButton button {
    width: 100%;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,.18);
}
.smop-hero {
    padding: 1.2rem 1.35rem;
    border-radius: 22px;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 58%, #0891b2 100%);
    color: white;
    box-shadow: 0 18px 45px rgba(15, 23, 42, .18);
    margin-bottom: 1rem;
}
.smop-hero h1 {
    margin: 0;
    font-size: 2rem;
    letter-spacing: -.03em;
}
.smop-hero p {
    margin: .35rem 0 0 0;
    color: rgba(255,255,255,.82);
}
.smop-card {
    background: white;
    border: 1px solid var(--smop-border);
    border-radius: 18px;
    padding: 1rem 1.1rem;
    box-shadow: 0 8px 28px rgba(15, 23, 42, .07);
    margin-bottom: .8rem;
}
.smop-card-title {
    color: #475569;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    margin-bottom: .35rem;
}
.smop-card-value {
    color: #0f172a;
    font-size: 1.42rem;
    font-weight: 760;
    line-height: 1.15;
}
.smop-card-caption {
    color: var(--smop-muted);
    font-size: .86rem;
    margin-top: .25rem;
}
.smop-pill {
    display: inline-flex;
    align-items: center;
    gap: .35rem;
    padding: .22rem .62rem;
    border-radius: 999px;
    font-size: .78rem;
    font-weight: 700;
    margin-right: .35rem;
    margin-bottom: .35rem;
}
.smop-pill-ok {
    color: #065f46;
    background: #d1fae5;
    border: 1px solid #a7f3d0;
}
.smop-pill-warn {
    color: #92400e;
    background: #fef3c7;
    border: 1px solid #fde68a;
}
.smop-pill-risk {
    color: #991b1b;
    background: #fee2e2;
    border: 1px solid #fecaca;
}
.smop-pill-info {
    color: #1e40af;
    background: #dbeafe;
    border: 1px solid #bfdbfe;
}
.smop-section-note {
    padding: .8rem 1rem;
    border-left: 4px solid #2563eb;
    background: #eff6ff;
    border-radius: 10px;
    color: #1e3a8a;
    margin: .5rem 0 1rem;
}
.smop-tiny {
    color: #64748b;
    font-size: .82rem;
}
[data-testid="stMetricValue"] {
    color: #0f172a;
    font-weight: 760;
}
[data-testid="stMetricLabel"] {
    color: #475569;
}
div[data-testid="stDataFrame"] {
    border: 1px solid var(--smop-border);
    border-radius: 12px;
    overflow: hidden;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def html_card(title: str, value: Any, caption: str = "") -> str:
    """Return a compact metric card as HTML."""
    safe_title = escape(str(title))
    safe_value = escape(str(value))
    safe_caption = escape(str(caption))
    return (
        '<div class="smop-card">'
        f'<div class="smop-card-title">{safe_title}</div>'
        f'<div class="smop-card-value">{safe_value}</div>'
        f'<div class="smop-card-caption">{safe_caption}</div>'
        '</div>'
    )


def render_card(title: str, value: Any, caption: str = "") -> None:
    """Render a compact production-style metric card."""
    st.markdown(html_card(title, value, caption), unsafe_allow_html=True)


def status_pill(label: str, tone: str = "info") -> str:
    """Return a status pill as HTML."""
    safe_label = escape(str(label))
    safe_tone = tone if tone in {"ok", "warn", "risk", "info"} else "info"
    return f'<span class="smop-pill smop-pill-{safe_tone}">{safe_label}</span>'


def render_status_pills(items: list[tuple[str, str]]) -> None:
    """Render multiple status pills on one line."""
    st.markdown(" ".join(status_pill(label, tone) for label, tone in items), unsafe_allow_html=True)


def first_available_timestamp(tables: dict[str, pd.DataFrame], column: str = "timestamp", latest: bool = True) -> pd.Timestamp | None:
    """Find the earliest or latest timestamp across sensor and production tables."""
    values: list[pd.Timestamp] = []
    for name in ["sensor", "production", "predictions", "alerts"]:
        df = tables.get(name, pd.DataFrame())
        if not df.empty and column in df.columns:
            parsed = pd.to_datetime(df[column], errors="coerce", utc=True).dropna()
            values.extend(parsed.tolist())
    if not values:
        return None
    return max(values) if latest else min(values)


def format_age(ts: pd.Timestamp | None) -> str:
    """Return a human-friendly age for a UTC timestamp."""
    if ts is None or pd.isna(ts):
        return "N/A"
    try:
        delta = pd.Timestamp.now(tz="UTC") - pd.Timestamp(ts)
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 48:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return "N/A"


def derive_ingestion_state(last_ts: pd.Timestamp | None) -> tuple[str, str, str]:
    """Return display label, tone, and explanation for current ingestion freshness."""
    if last_ts is None:
        return "Waiting for data", "warn", "No sensor or production events have been ingested."
    try:
        age_seconds = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(last_ts)).total_seconds()
    except Exception:
        return "Timestamp unavailable", "warn", "The latest event timestamp could not be parsed."
    if age_seconds < 120:
        return "Live stream active", "ok", "Recent events are landing in the system."
    if age_seconds < 3600:
        return "Stream delayed", "warn", "Events exist, but the latest timestamp is older than the live target."
    return "Replay / offline dataset", "info", "Data is available for review, but it is not a live stream."


def build_action_queue(
    latest_predictions: pd.DataFrame,
    alerts: pd.DataFrame,
    issues: pd.DataFrame,
    max_items: int = 8,
) -> pd.DataFrame:
    """Create an operator-style action queue from predictions, alerts, and data quality signals."""
    rows: list[dict[str, Any]] = []

    if not latest_predictions.empty:
        for _, row in latest_predictions.iterrows():
            risk = str(row.get("risk_level", "")).lower()
            if risk in {"high", "critical"}:
                rows.append(
                    {
                        "priority": "P1" if risk == "critical" else "P2",
                        "area": f"{row.get('line_id', 'N/A')} / {row.get('station_id', 'N/A')}",
                        "asset": row.get("machine_id", "N/A"),
                        "signal": f"{risk.upper()} risk, health {format_metric(row.get('health_score'))}",
                        "suggested_action": row.get("recommended_action") or "Inspect asset and validate current process condition.",
                    }
                )

    if not alerts.empty:
        for _, row in alerts.head(max_items).iterrows():
            severity = str(row.get("severity", "")).lower()
            rows.append(
                {
                    "priority": "P1" if severity == "critical" else "P2",
                    "area": f"{row.get('line_id', 'N/A')} / {row.get('station_id', 'N/A')}",
                    "asset": row.get("machine_id", "N/A"),
                    "signal": f"Anomaly alert: {row.get('anomaly_score', 'N/A')}",
                    "suggested_action": row.get("message") or "Review recent sensor and production trend before shift handover.",
                }
            )

    if not issues.empty:
        severe = issues[issues.get("severity", pd.Series(dtype=str)).astype(str).str.lower().isin(["high", "critical"])] if "severity" in issues.columns else pd.DataFrame()
        source = severe if not severe.empty else issues.head(3)
        for _, row in source.head(3).iterrows():
            rows.append(
                {
                    "priority": "P3",
                    "area": f"{row.get('line_id', 'N/A')} / {row.get('station_id', 'N/A')}",
                    "asset": row.get("machine_id", row.get("entity_id", "N/A")),
                    "signal": f"Data quality: {row.get('issue_type', 'N/A')}",
                    "suggested_action": "Verify data acquisition channel before using model output for decisions.",
                }
            )

    if not rows:
        return pd.DataFrame(
            [
                {
                    "priority": "Monitor",
                    "area": "All lines",
                    "asset": "System",
                    "signal": "No high-priority action generated",
                    "suggested_action": "Continue collecting data, refresh model outputs, and review dashboard at shift handover.",
                }
            ]
        )
    priority_order = {"P1": 0, "P2": 1, "P3": 2, "Monitor": 3}
    out = pd.DataFrame(rows).drop_duplicates()
    out["_order"] = out["priority"].map(priority_order).fillna(9)
    return out.sort_values(["_order", "area"]).drop(columns=["_order"]).head(max_items)


def render_ops_context(tables: dict[str, pd.DataFrame]) -> None:
    """Render the operational context strip below the main header."""
    sensor = tables.get("sensor", pd.DataFrame())
    production = tables.get("production", pd.DataFrame())
    models = tables.get("models", pd.DataFrame())
    predictions = tables.get("predictions", pd.DataFrame())
    alerts = tables.get("alerts", pd.DataFrame())

    first_ts = first_available_timestamp(tables, latest=False)
    last_ts = first_available_timestamp(tables, latest=True)
    state, tone, explanation = derive_ingestion_state(last_ts)
    trained_models = models["model_name"].nunique() if not models.empty and "model_name" in models.columns else len(models)
    high_alerts = 0
    if not alerts.empty and "severity" in alerts.columns:
        high_alerts = int(alerts["severity"].astype(str).str.lower().isin(["high", "critical"]).sum())
    if high_alerts == 0 and not predictions.empty and "risk_level" in predictions.columns:
        high_alerts = int(predictions["risk_level"].astype(str).str.lower().isin(["high", "critical"]).sum())

    render_status_pills(
        [
            (state, tone),
            (SYSTEM_PROFILE["mode"], "info"),
            (f"{len(sensor):,} sensor events", "info"),
            (f"{len(production):,} production events", "info"),
            (f"{trained_models} model run(s)", "ok" if trained_models else "warn"),
        ]
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_card("Data freshness", format_age(last_ts), explanation)
    with c2:
        span = "N/A" if first_ts is None or last_ts is None else f"{first_ts.date()} → {last_ts.date()}"
        render_card("Data window", span, "Timestamp range across operational tables.")
    with c3:
        render_card("Risk posture", f"{high_alerts} high signals", "High/critical predictions or anomaly alerts.")
    with c4:
        render_card("Database", get_db_path().name, "Local system-of-record for the prototype.")


def project_root() -> Path:
    """Return repository root from dashboard/app.py."""
    return Path(__file__).resolve().parents[1]


def get_db_path() -> Path:
    """Resolve SQLite path from environment or default repository location."""
    return Path(os.environ.get("SMOP_DB_PATH", project_root() / "database" / "smart_manufacturing.db"))


def connect_db() -> sqlite3.Connection:
    """Open a SQLite connection with dict-like rows."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(table_name: str) -> bool:
    """Return True when a SQLite table exists."""
    try:
        with connect_db() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            return row is not None
    except Exception:
        return False


@st.cache_data(ttl=5)
def read_table(table_name: str, order_by: str | None = None, limit: int | None = None) -> pd.DataFrame:
    """Read a table safely from SQLite.

    Empty DataFrames are returned when the database or table is not ready.
    """
    if not table_exists(table_name):
        return pd.DataFrame()

    try:
        query = f"SELECT * FROM {table_name}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with connect_db() as conn:
            df = pd.read_sql_query(query, conn)
        return normalize_timestamps(df)
    except Exception as exc:
        st.warning(f"Could not read table `{table_name}`: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def read_query(query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    """Read a custom SQL query safely."""
    try:
        with connect_db() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return normalize_timestamps(df)
    except Exception as exc:
        st.warning(f"Query failed: {exc}")
        return pd.DataFrame()


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Convert common timestamp columns to pandas datetime."""
    out = df.copy()
    for col in ["timestamp", "created_at", "detected_at", "started_at", "completed_at", "event_timestamp", "sensor_timestamp"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce", utc=True)
    return out


def show_empty(message: str, command: str | None = None) -> None:
    """Show a consistent empty-state message."""
    st.info(message)
    if command:
        st.code(command, language="bash")


def plot_line(df: pd.DataFrame, x: str, y: str | list[str], color: str | None = None, title: str = "") -> None:
    """Render a line chart with Plotly when available, otherwise Streamlit line chart."""
    if df.empty or x not in df.columns:
        show_empty("No data available for this chart yet.")
        return

    try:
        if px is not None:
            fig = px.line(df, x=x, y=y, color=color, title=title, markers=False)
            fig.update_layout(
                height=390,
                template="plotly_white",
                hovermode="x unified",
                legend_title_text="",
                margin=dict(l=10, r=10, t=48, b=10),
                font=dict(size=13),
            )
            fig.update_traces(line=dict(width=2))
            st.plotly_chart(fig, use_container_width=True)
        else:
            cols = [y] if isinstance(y, str) else y
            st.line_chart(df.set_index(x)[cols])
    except Exception as exc:
        st.warning(f"Chart could not be rendered: {exc}")


def plot_bar(df: pd.DataFrame, x: str, y: str, color: str | None = None, title: str = "") -> None:
    """Render a bar chart with fallback."""
    if df.empty or x not in df.columns or y not in df.columns:
        show_empty("No data available for this chart yet.")
        return

    try:
        if px is not None:
            fig = px.bar(df, x=x, y=y, color=color, title=title)
            fig.update_layout(
                height=360,
                template="plotly_white",
                legend_title_text="",
                margin=dict(l=10, r=10, t=48, b=10),
                font=dict(size=13),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(df.set_index(x)[y])
    except Exception as exc:
        st.warning(f"Chart could not be rendered: {exc}")


def latest_by_group(df: pd.DataFrame, group_cols: list[str], timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Return the latest row per group."""
    if df.empty or timestamp_col not in df.columns:
        return pd.DataFrame()
    available_groups = [c for c in group_cols if c in df.columns]
    if not available_groups:
        return df.sort_values(timestamp_col).tail(1)
    return df.sort_values(timestamp_col).groupby(available_groups, as_index=False).tail(1)


def count_issue(issues: pd.DataFrame, issue_type: str) -> int:
    """Count data quality issues by type."""
    if issues.empty or "issue_type" not in issues.columns:
        return 0
    return int((issues["issue_type"] == issue_type).sum())


def safe_mean(df: pd.DataFrame, column: str) -> float | None:
    """Return numeric mean or None."""
    if df.empty or column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def format_metric(value: Any, suffix: str = "", decimals: int = 2) -> str:
    """Format metric value for display."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except Exception:
        return str(value)


def load_metrics_json_from_row(row: pd.Series) -> dict[str, Any]:
    """Parse metrics_json from a model run row."""
    value = row.get("metrics_json")
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def make_markdown_report(
    sensor: pd.DataFrame,
    production: pd.DataFrame,
    predictions: pd.DataFrame,
    alerts: pd.DataFrame,
    issues: pd.DataFrame,
    model_runs: pd.DataFrame,
) -> str:
    """Build a lightweight Markdown operational report."""
    latest_prediction = latest_by_group(predictions, ["machine_id"], "timestamp")
    avg_health = safe_mean(latest_prediction, "health_score")
    avg_rul = safe_mean(latest_prediction, "rul_estimate_hours")
    anomaly_count = len(alerts) if not alerts.empty else int(pd.to_numeric(predictions.get("anomaly_flag", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not predictions.empty else 0

    generated_at = datetime.now(timezone.utc).isoformat()
    last_prediction_time = None
    if not predictions.empty and "timestamp" in predictions.columns:
        parsed_ts = pd.to_datetime(predictions["timestamp"], errors="coerce", utc=True).dropna()
        last_prediction_time = parsed_ts.max().isoformat() if not parsed_ts.empty else None

    action_queue = build_action_queue(latest_prediction, alerts, issues, max_items=5)
    action_lines = "\n".join(
        f"- **{row['priority']}** | {row['area']} | {row['asset']} | {row['signal']} — {row['suggested_action']}"
        for _, row in action_queue.iterrows()
    )

    return f"""# Smart Manufacturing AI Operations Report

Generated at: `{generated_at}`

## Data policy

{DISCLAIMER}

## Shift handover summary

- Sensor readings: **{len(sensor)}**
- Production events: **{len(production)}**
- Predictions: **{len(predictions)}**
- Anomaly alerts: **{len(alerts)}**
- Data quality issues: **{len(issues)}**
- Model runs: **{len(model_runs)}**
- Average health score: **{format_metric(avg_health)}**
- Average RUL hours: **{format_metric(avg_rul)}**
- Anomaly count: **{anomaly_count}**
- Latest prediction timestamp: **{last_prediction_time or "N/A"}**

## Operator action queue

{action_lines}

## Recommended operating rhythm

1. Confirm C# collector and API are receiving records continuously.
2. Review data quality issues before interpreting ML output.
3. Rebuild the processed dataset after a meaningful data window has accumulated.
4. Train models and compare registry metrics before using a new artifact.
5. Treat all outputs as simulated prototype evidence, not validated production recommendations.
"""


def download_dataframe(df: pd.DataFrame, file_name: str, label: str) -> None:
    """Render a CSV download button for a DataFrame."""
    if df.empty:
        st.caption(f"No data available for {label}.")
        return
    st.download_button(
        label=f"Download {label} CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=file_name,
        mime="text/csv",
    )


def render_header() -> None:
    """Render dashboard header and sidebar."""
    st.set_page_config(page_title=APP_TITLE, layout="wide", page_icon="🏭")
    inject_global_style()
    st.markdown(
        f"""
<div class="smop-hero">
  <div class="smop-tiny">SMART MANUFACTURING · AI OPERATIONS COMMAND CENTER</div>
  <h1>🏭 {escape(APP_TITLE)}</h1>
  <p>{escape(DISCLAIMER)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("## 🏭 SMOP Control")
    st.sidebar.caption(f"Site: **{SYSTEM_PROFILE['site']}**")
    st.sidebar.caption(f"Area: **{SYSTEM_PROFILE['area']}**")
    st.sidebar.caption(f"SQLite: `{get_db_path()}`")
    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.caption("Run order")
    st.sidebar.code(
        "bash scripts/run_api.sh\n"
        "cd acquisition-csharp/SensorCollector && dotnet run\n"
        "python backend-python/src/data/preprocessing.py\n"
        "python backend-python/src/models/train_all.py",
        language="bash",
    )


def load_all_tables() -> dict[str, pd.DataFrame]:
    """Load all dashboard-relevant tables."""
    return {
        "sensor": read_table("sensor_readings", order_by="timestamp"),
        "production": read_table("production_events", order_by="timestamp"),
        "issues": read_table("data_quality_issues", order_by="detected_at DESC"),
        "logs": read_table("data_acquisition_logs", order_by="created_at DESC"),
        "models": read_table("model_training_runs", order_by="id DESC"),
        "predictions": read_table("predictions", order_by="id DESC"),
        "alerts": read_table("anomaly_alerts", order_by="id DESC"),
        "hints": read_table("diagnostic_hints", order_by="id DESC"),
    }


def page_executive_overview(tables: dict[str, pd.DataFrame]) -> None:
    """Render executive overview page."""
    st.header("1. Executive Overview")

    sensor = tables["sensor"]
    production = tables["production"]
    predictions = tables["predictions"]
    alerts = tables["alerts"]

    latest_predictions = latest_by_group(predictions, ["machine_id"], "timestamp")
    total_machines = sensor["machine_id"].nunique() if "machine_id" in sensor.columns and not sensor.empty else 0
    total_lines = pd.concat(
        [
            sensor[["line_id"]] if "line_id" in sensor.columns else pd.DataFrame(columns=["line_id"]),
            production[["line_id"]] if "line_id" in production.columns else pd.DataFrame(columns=["line_id"]),
        ],
        ignore_index=True,
    )["line_id"].nunique()

    critical_machines = 0
    if not latest_predictions.empty and "risk_level" in latest_predictions.columns:
        critical_machines = int(latest_predictions["risk_level"].isin(["high", "critical"]).sum())

    avg_health = safe_mean(latest_predictions, "health_score")
    anomaly_count = len(alerts) if not alerts.empty else int(pd.to_numeric(predictions.get("anomaly_flag", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not predictions.empty else 0
    avg_rul = safe_mean(latest_predictions, "rul_estimate_hours")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total machines", total_machines)
    c2.metric("Total lines", total_lines)
    c3.metric("Critical machines", critical_machines)
    c4.metric("Avg health", format_metric(avg_health))
    c5.metric("Anomaly count", anomaly_count)
    c6.metric("Avg RUL hours", format_metric(avg_rul))

    st.markdown(
        '<div class="smop-section-note">This page is designed as a shift-handover view: current line posture, critical assets, and the next actions an operations lead would ask for.</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Shift handover action queue")
    action_queue = build_action_queue(latest_predictions, alerts, tables["issues"])
    st.dataframe(action_queue, use_container_width=True, hide_index=True)

    st.subheader("Line health summary")
    if latest_predictions.empty:
        show_empty(
            "No prediction records yet. Run model training and call prediction endpoints to populate line health.",
            "python backend-python/src/models/train_all.py",
        )
    else:
        summary = (
            latest_predictions.groupby("line_id", dropna=False)
            .agg(
                machines=("machine_id", "nunique"),
                avg_health_score=("health_score", "mean"),
                max_failure_probability=("failure_probability", "max"),
                min_rul_hours=("rul_estimate_hours", "min"),
            )
            .reset_index()
            .sort_values("avg_health_score")
        )
        st.dataframe(summary, use_container_width=True)
        plot_bar(summary, "line_id", "avg_health_score", title="Average Health Score by Line")

    st.subheader("Latest operational data")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Latest sensor readings")
        st.dataframe(sensor.sort_values("timestamp").tail(10) if not sensor.empty else pd.DataFrame(), use_container_width=True)
    with c2:
        st.caption("Latest production events")
        st.dataframe(production.sort_values("timestamp").tail(10) if not production.empty else pd.DataFrame(), use_container_width=True)


def page_data_acquisition_status(tables: dict[str, pd.DataFrame]) -> None:
    """Render data acquisition status page."""
    st.header("2. Data Acquisition Status")

    sensor = tables["sensor"]
    production = tables["production"]
    issues = tables["issues"]
    logs = tables["logs"]

    timestamps = []
    for df in [sensor, production]:
        if not df.empty and "timestamp" in df.columns:
            timestamps.extend(df["timestamp"].dropna().tolist())
    last_received = max(timestamps) if timestamps else None

    successful_ingestion_count = len(sensor) + len(production)
    failed_ingestion_count = 0
    if not logs.empty and "status" in logs.columns:
        failed_ingestion_count = int(logs["status"].astype(str).str.lower().isin(["failed", "error"]).sum())

    delayed_readings = count_issue(issues, "delayed_reading")
    buffered_proxy = (
        count_issue(issues, "timestamp_gap")
        + count_issue(issues, "sensor_dropout")
        + failed_ingestion_count
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Last received timestamp", str(last_received) if last_received is not None else "N/A")
    c2.metric("Successful ingestion count", successful_ingestion_count)
    c3.metric("Failed ingestion count", failed_ingestion_count)
    c4.metric("Buffered records proxy", buffered_proxy)
    c5.metric("Delayed readings", delayed_readings)

    st.subheader("Collector status")
    if sensor.empty and production.empty:
        show_empty(
            "No ingested data found. Start FastAPI and run the C# collector.",
            "bash scripts/run_api.sh\ncd acquisition-csharp/SensorCollector && dotnet run",
        )
    else:
        freshness = "active"
        if last_received is not None:
            age_seconds = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(last_received)).total_seconds()
            freshness = "active" if age_seconds < 120 else "stale"
        render_status_pills([(f"Collector status proxy: {freshness}", "ok" if freshness == "active" else "warn")])
        st.caption("Status is inferred from the latest SQLite timestamp and should be replaced by heartbeat telemetry in a production deployment.")

        combined = []
        if not sensor.empty:
            s = sensor[["timestamp"]].copy()
            s["type"] = "sensor"
            combined.append(s)
        if not production.empty:
            p = production[["timestamp"]].copy()
            p["type"] = "production"
            combined.append(p)
        if combined:
            ingest = pd.concat(combined, ignore_index=True).dropna(subset=["timestamp"])
            ingest["minute"] = ingest["timestamp"].dt.floor("min")
            counts = ingest.groupby(["minute", "type"]).size().reset_index(name="records")
            plot_line(counts, "minute", "records", color="type", title="Ingestion Records per Minute")

    st.subheader("Acquisition logs")
    if logs.empty:
        show_empty("No data_acquisition_logs rows yet. The C# collector logs locally; API logs can be added in future hardening.")
    else:
        st.dataframe(logs.head(200), use_container_width=True)


def page_line_monitoring(tables: dict[str, pd.DataFrame]) -> None:
    """Render line monitoring page."""
    st.header("3. Line Monitoring")
    production = tables["production"]

    if production.empty:
        show_empty(
            "No production events yet. Run C# collector after starting FastAPI.",
            "bash scripts/run_api.sh\ncd acquisition-csharp/SensorCollector && dotnet run",
        )
        return

    lines = sorted(production["line_id"].dropna().unique()) if "line_id" in production.columns else []
    selected_line = st.selectbox("Select line", lines) if lines else None
    line_df = production[production["line_id"] == selected_line].copy() if selected_line else production.copy()
    line_df = line_df.sort_values("timestamp")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Events", len(line_df))
    c2.metric("Avg cycle time", format_metric(safe_mean(line_df, "cycle_time_sec"), "s"))
    c3.metric("Avg station yield", format_metric(safe_mean(line_df, "station_yield"), decimals=4))
    c4.metric("Total downtime min", format_metric(pd.to_numeric(line_df.get("downtime_minutes", pd.Series(dtype=float)), errors="coerce").sum(), decimals=2))

    st.subheader("Throughput vs target")
    if "target_throughput" in line_df.columns and "throughput_count" in line_df.columns:
        plot_line(line_df, "timestamp", ["throughput_count", "target_throughput"], color="station_id" if "station_id" in line_df.columns else None, title="Throughput vs Target")

    st.subheader("Cycle time trend")
    plot_line(line_df, "timestamp", "cycle_time_sec", color="station_id" if "station_id" in line_df.columns else None, title="Cycle Time Trend")

    st.subheader("Station yield trend")
    plot_line(line_df, "timestamp", "station_yield", color="station_id" if "station_id" in line_df.columns else None, title="Station Yield Trend")

    st.subheader("Reject / defect rate trend")
    y_col = "defect_rate" if "defect_rate" in line_df.columns else "reject_count"
    plot_line(line_df, "timestamp", y_col, color="station_id" if "station_id" in line_df.columns else None, title="Reject Rate / Defect Rate Trend")

    st.subheader("Micro stops and downtime")
    c1, c2 = st.columns(2)
    with c1:
        plot_line(line_df, "timestamp", "micro_stop_count", color="station_id" if "station_id" in line_df.columns else None, title="Micro Stop Count")
    with c2:
        plot_line(line_df, "timestamp", "downtime_minutes", color="station_id" if "station_id" in line_df.columns else None, title="Downtime Minutes")


def page_equipment_health(tables: dict[str, pd.DataFrame]) -> None:
    """Render equipment health page."""
    st.header("4. Equipment Health")
    sensor = tables["sensor"]
    predictions = tables["predictions"]

    if sensor.empty:
        show_empty("No sensor readings available. Start collector and ingestion first.")
        return

    machines = sorted(sensor["machine_id"].dropna().unique()) if "machine_id" in sensor.columns else []
    selected_machine = st.selectbox("Select machine", machines) if machines else None
    if not selected_machine:
        show_empty("No machine IDs available in sensor_readings.")
        return

    sensor_df = sensor[sensor["machine_id"] == selected_machine].sort_values("timestamp")
    pred_df = predictions[predictions["machine_id"] == selected_machine].sort_values("timestamp") if not predictions.empty and "machine_id" in predictions.columns else pd.DataFrame()
    latest_pred = pred_df.tail(1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Failure probability", format_metric(latest_pred["failure_probability"].iloc[0] if not latest_pred.empty and "failure_probability" in latest_pred.columns else None))
    c2.metric("RUL hours", format_metric(latest_pred["rul_estimate_hours"].iloc[0] if not latest_pred.empty and "rul_estimate_hours" in latest_pred.columns else None))
    c3.metric("Health score", format_metric(latest_pred["health_score"].iloc[0] if not latest_pred.empty and "health_score" in latest_pred.columns else None))
    c4.metric("Risk level", latest_pred["risk_level"].iloc[0] if not latest_pred.empty and "risk_level" in latest_pred.columns else "N/A")

    st.subheader("Sensor trends")
    sensor_cols = [c for c in ["vibration_rms", "process_temperature", "motor_current", "torque", "tool_wear"] if c in sensor_df.columns]
    if sensor_cols:
        plot_line(sensor_df, "timestamp", sensor_cols, color="station_id" if "station_id" in sensor_df.columns else None, title=f"Sensor Trends - {selected_machine}")

    st.subheader("Recommended action")
    if latest_pred.empty:
        show_empty(
            "No prediction record for this machine yet. Train models and call prediction endpoints.",
            "python backend-python/src/models/train_all.py",
        )
    else:
        action = latest_pred.get("recommended_action", pd.Series(["N/A"])).iloc[0]
        hint = latest_pred.get("diagnostic_hint", pd.Series(["N/A"])).iloc[0]
        st.markdown(html_card("Recommended maintenance action", action, "Generated from failure, RUL, anomaly, and health-score signals."), unsafe_allow_html=True)
        st.caption("Diagnostic hint")
        st.info(hint)

    st.subheader("Recent prediction history")
    st.dataframe(pred_df.tail(50), use_container_width=True)


def page_process_anomaly(tables: dict[str, pd.DataFrame]) -> None:
    """Render process anomaly page."""
    st.header("5. Process Anomaly")
    alerts = tables["alerts"]
    predictions = tables["predictions"]
    hints = tables["hints"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Alerts", len(alerts))
    c2.metric("Anomaly flags", int(pd.to_numeric(predictions.get("anomaly_flag", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not predictions.empty else 0)
    c3.metric("Diagnostic hints", len(hints))

    st.subheader("Anomaly timeline")
    if not predictions.empty and "anomaly_score" in predictions.columns:
        plot_line(predictions.sort_values("timestamp"), "timestamp", "anomaly_score", color="station_id" if "station_id" in predictions.columns else None, title="Anomaly Score Timeline")
    elif not alerts.empty:
        plot_line(alerts.sort_values("timestamp"), "timestamp", "anomaly_score", color="station_id" if "station_id" in alerts.columns else None, title="Anomaly Alert Timeline")
    else:
        show_empty("No anomaly predictions or alerts yet. Train models and call /detect/anomaly.")

    st.subheader("Affected line / station")
    if alerts.empty:
        show_empty("No anomaly_alerts rows yet.")
    else:
        cols = [c for c in ["timestamp", "machine_id", "line_id", "station_id", "anomaly_score", "severity", "message", "source"] if c in alerts.columns]
        st.dataframe(alerts[cols].head(200), use_container_width=True)

    st.subheader("Diagnostic hints")
    source = hints if not hints.empty else predictions
    if source.empty:
        show_empty("No diagnostic hints available yet.")
    else:
        cols = [c for c in ["timestamp", "machine_id", "line_id", "station_id", "hint", "diagnostic_hint", "recommended_action"] if c in source.columns]
        st.dataframe(source[cols].head(200), use_container_width=True)


def page_data_quality(tables: dict[str, pd.DataFrame]) -> None:
    """Render data quality page."""
    st.header("6. Data Quality")
    issues = tables["issues"]
    sensor = tables["sensor"]
    production = tables["production"]

    missing_values = count_issue(issues, "missing_value")
    duplicates = count_issue(issues, "duplicate_timestamp")
    stuck = count_issue(issues, "stuck_sensor")
    gaps = count_issue(issues, "timestamp_gap")
    dropout = count_issue(issues, "sensor_dropout")
    impossible = count_issue(issues, "impossible_value")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Missing values", missing_values)
    c2.metric("Duplicate timestamps", duplicates)
    c3.metric("Stuck sensor", stuck)
    c4.metric("Timestamp gaps", gaps)
    c5.metric("Sensor dropout", dropout)
    c6.metric("Impossible values", impossible)

    if issues.empty:
        show_empty(
            "No data quality issues recorded yet. Run preprocessing to populate data_quality_issues.",
            "python backend-python/src/data/preprocessing.py",
        )
        if not sensor.empty or not production.empty:
            st.caption("Raw tables contain data, but quality checks have not been persisted yet.")
        return

    st.subheader("Issue counts by type")
    counts = issues.groupby("issue_type").size().reset_index(name="count").sort_values("count", ascending=False)
    plot_bar(counts, "issue_type", "count", title="Data Quality Issues by Type")

    st.subheader("Issue severity")
    if "severity" in issues.columns:
        severity = issues.groupby("severity").size().reset_index(name="count")
        plot_bar(severity, "severity", "count", title="Issue Severity")

    st.subheader("Recent quality issues")
    cols = [c for c in ["detected_at", "issue_type", "severity", "entity_type", "machine_id", "line_id", "station_id", "timestamp", "details_json"] if c in issues.columns]
    st.dataframe(issues[cols].head(300), use_container_width=True)


def page_model_training_registry(tables: dict[str, pd.DataFrame]) -> None:
    """Render model training and registry page."""
    st.header("7. Model Training & Registry")
    model_runs = tables["models"]

    st.subheader("Training command")
    st.markdown(
        '<div class="smop-section-note">Model training is intentionally kept outside the dashboard process. This mirrors production separation between operator UI and batch/ML jobs.</div>',
        unsafe_allow_html=True,
    )
    st.code("python backend-python/src/models/train_all.py", language="bash")

    if st.button("Show training command reminder"):
        st.success("Run the command above in your terminal. Streamlit does not train in-process to keep the dashboard safe and predictable.")

    if model_runs.empty:
        show_empty("No model_training_runs rows yet. Run model training after preprocessing.")
        return

    st.subheader("Model runs")
    cols = [c for c in ["id", "model_name", "model_type", "model_version", "artifact_path", "training_rows", "test_rows", "completed_at", "status"] if c in model_runs.columns]
    st.dataframe(model_runs[cols], use_container_width=True)

    st.subheader("Metrics")
    selected_id = st.selectbox("Select model run ID", model_runs["id"].tolist())
    selected = model_runs[model_runs["id"] == selected_id].iloc[0]
    metrics = load_metrics_json_from_row(selected)
    if metrics:
        st.json(metrics)
    else:
        st.info("No metrics_json available for this run.")

    st.subheader("Feature importance")
    artifact_path = selected.get("artifact_path")
    if isinstance(artifact_path, str) and artifact_path:
        show_feature_importance(Path(artifact_path))
    else:
        st.info("No artifact_path found for selected model run.")


def show_feature_importance(artifact_path: Path) -> None:
    """Attempt to load a joblib model and display feature importances if available."""
    try:
        import joblib
    except Exception:
        st.info("joblib is not installed in this environment.")
        return

    if not artifact_path.is_absolute():
        artifact_path = project_root() / artifact_path
    if not artifact_path.exists():
        st.info(f"Model artifact not found: {artifact_path}")
        return

    try:
        bundle = joblib.load(artifact_path)
        model = bundle.get("model")
        feature_columns = bundle.get("feature_columns", [])
        estimator = getattr(model, "named_steps", {}).get("model", model)
        importances = getattr(estimator, "feature_importances_", None)
        if importances is None:
            st.info("Selected model does not expose feature_importances_. Logistic regression and some pipelines may not provide it.")
            return
        importance_df = pd.DataFrame({"feature": feature_columns, "importance": importances}).sort_values("importance", ascending=False).head(25)
        st.dataframe(importance_df, use_container_width=True)
        plot_bar(importance_df, "feature", "importance", title="Top Feature Importances")
    except Exception as exc:
        st.warning(f"Could not load feature importance: {exc}")


def page_reports_edge_deployment(tables: dict[str, pd.DataFrame]) -> None:
    """Render reports and edge deployment page."""
    st.header("8. Reports / Edge Deployment")

    sensor = tables["sensor"]
    production = tables["production"]
    predictions = tables["predictions"]
    alerts = tables["alerts"]
    issues = tables["issues"]
    model_runs = tables["models"]

    st.subheader("Export CSV")
    c1, c2, c3 = st.columns(3)
    with c1:
        download_dataframe(predictions, "predictions_export.csv", "predictions")
    with c2:
        download_dataframe(alerts, "anomaly_alerts_export.csv", "alerts")
    with c3:
        download_dataframe(issues, "data_quality_issues_export.csv", "data quality issues")

    st.subheader("Markdown report")
    report_md = make_markdown_report(sensor, production, predictions, alerts, issues, model_runs)
    st.download_button(
        "Download Markdown Report",
        data=report_md.encode("utf-8"),
        file_name="smart_manufacturing_ai_operations_report.md",
        mime="text/markdown",
    )

    if st.button("Save report to reports/dashboard_report.md"):
        report_path = project_root() / "reports" / "dashboard_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding="utf-8")
        st.success(f"Saved report: {report_path}")

    st.subheader("Edge deployment architecture")
    st.markdown(
        """
```text
Factory floor / edge PC
  C# SensorCollector
    -> reads machine/station config
    -> generates or collects sensor and production events
    -> buffers JSONL if network/API is unavailable
    -> posts to FastAPI over HTTP

Local analytics node
  FastAPI ingestion + inference
    -> validates payloads
    -> writes SQLite
    -> loads model artifacts
    -> returns failure/RUL/anomaly predictions

Operations dashboard
  Streamlit
    -> reads SQLite/API
    -> visualizes health, anomalies, quality, and model registry
    -> exports CSV/Markdown report
```
        """
    )

    st.subheader("Limitations")
    st.warning(
        """
This is a simulated-data working prototype. It is not validated on real machines,
does not use real Seagate data, does not use proprietary factory data, and is not
a closed-loop control system. A real deployment would require OT/IT integration,
security review, historian/PLC integration, real maintenance labels, process
owner review, and factory acceptance testing.
        """
    )


def main() -> None:
    """Streamlit entrypoint."""
    render_header()
    tables = load_all_tables()
    render_ops_context(tables)

    pages = {
        "Executive Overview": page_executive_overview,
        "Data Acquisition Status": page_data_acquisition_status,
        "Line Monitoring": page_line_monitoring,
        "Equipment Health": page_equipment_health,
        "Process Anomaly": page_process_anomaly,
        "Data Quality": page_data_quality,
        "Model Training & Registry": page_model_training_registry,
        "Reports / Edge Deployment": page_reports_edge_deployment,
    }

    page_labels = [f"{PAGE_ICONS[name]} {name}" for name in pages]
    selected_label = st.sidebar.radio("Pages", page_labels)
    page_name = selected_label.split(" ", 1)[1]
    pages[page_name](tables)


if __name__ == "__main__":
    main()
