from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

import pandas as pd


EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def load_dashboard_module():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("dashboard_app", root / "dashboard" / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dashboard_report_generation_empty_safe():
    app = load_dashboard_module()
    report = app.make_markdown_report(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert "Factory Intelligence Operations Report" in report
    assert "DEMO data" in report
    assert "stored collector/API records" in report


def test_dashboard_localized_report_generation_empty_safe():
    app = load_dashboard_module()
    report = app.make_markdown_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        lang="th",
    )
    assert "รายงานศูนย์ควบคุมข้อมูลการผลิต" in report
    assert "DEMO data" in report
    assert "collector/API บันทึกไว้" in report


def test_dashboard_machine_snapshot_uses_sensor_records():
    app = load_dashboard_module()
    sensor = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2026-05-18T08:00:00Z"),
                "machine_id": "M-01",
                "line_id": "LINE-A",
                "station_id": "ST-01",
                "vibration_rms": 2.8,
                "process_temperature": 73.0,
                "motor_current": 14.0,
                "torque": 25.0,
                "tool_wear": 68.0,
            }
        ]
    )
    production = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2026-05-18T08:00:05Z"),
                "line_id": "LINE-A",
                "station_id": "ST-01",
                "cycle_time_sec": 6.2,
                "station_yield": 0.971,
                "defect_rate": 0.012,
            }
        ]
    )

    snapshot = app.build_machine_snapshot(sensor, production, pd.DataFrame(), "en")

    assert snapshot.loc[0, "machine_id"] == "M-01"
    assert snapshot.loc[0, "source"] == "sensor-derived"
    assert snapshot.loc[0, "condition_score"] < 100
    assert snapshot.loc[0, "derived_anomaly_index"] > 0
    assert snapshot.loc[0, "cycle_time_sec"] == 6.2


def test_dashboard_has_no_emoji_in_source():
    root = Path(__file__).resolve().parents[3]
    source = (root / "dashboard" / "app.py").read_text(encoding="utf-8")
    assert EMOJI_RE.search(source) is None


def test_dashboard_source_omits_banned_company_name():
    root = Path(__file__).resolve().parents[3]
    source = (root / "dashboard" / "app.py").read_text(encoding="utf-8")
    banned = "".join(chr(code) for code in [83, 101, 97, 103, 97, 116, 101])
    assert banned not in source


def test_dashboard_translation_keys_cover_all_languages():
    app = load_dashboard_module()
    expected_languages = {"th", "en", "zh", "ja"}
    assert set(app.LANGUAGE_OPTIONS) == expected_languages
    english_keys = set(app.TEXT["en"])
    for lang in expected_languages:
        assert english_keys <= set(app.TEXT[lang])


def test_dashboard_workflow_board_uses_case_records():
    app = load_dashboard_module()
    cases = pd.DataFrame(
        [
            {
                "case_id": "CASE-TEST",
                "title": "Temperature signal on MTR-01",
                "severity": "high",
                "status": "new",
                "owner": "shift-lead",
                "machine_id": "MTR-01",
                "line_id": "LINE-A",
                "station_id": "ST-01",
                "source_type": "sensor-derived",
                "due_at": pd.Timestamp("2026-05-18T12:00:00Z"),
            }
        ]
    )

    html = app.render_workflow_board_html(cases, "en")

    assert "Temperature signal on MTR-01" in html
    assert "shift-lead" in html
    assert "cmd-workflow-board" in html


def test_dashboard_enterprise_summary_uses_security_records():
    app = load_dashboard_module()
    users = pd.DataFrame([{"user_id": "operator", "role": "operator"}, {"user_id": "supervisor", "role": "supervisor"}])
    approvals = pd.DataFrame([{"approval_id": "APR-1", "status": "pending"}])
    notifications = pd.DataFrame([{"notification_id": "NTF-1", "status": "queued"}])
    outbox = pd.DataFrame([{"outbox_id": 1, "status": "queued", "target_system": "cmms"}])

    html = app.render_enterprise_summary_html(users, approvals, notifications, outbox, "en")

    assert "Role-backed users" in html
    assert "Pending approvals" in html
    assert "Integration outbox" in html


def test_dashboard_connector_health_summary_uses_dispatch_status():
    app = load_dashboard_module()
    outbox = pd.DataFrame(
        [
            {"outbox_id": 1, "target_system": "cmms", "status": "sent"},
            {"outbox_id": 2, "target_system": "mes", "status": "not_configured"},
            {"outbox_id": 3, "target_system": "cmms", "status": "retrying"},
        ]
    )
    html = app.render_connector_health_html(outbox, "en")

    assert "CMMS connector" in html
    assert "MES connector" in html
    assert "Sent" in html
    assert "Not configured" in html


def test_dashboard_command_metric_card_includes_trust_badge():
    app = load_dashboard_module()
    html = app.command_metric_card(
        "Risk posture",
        "2",
        "derived signals",
        trust_levels=[app.TRUST_DERIVED, app.TRUST_MODEL_UNAVAILABLE],
        lang="en",
    )
    assert "trust-badge" in html
    assert "Derived" in html
    assert "Model unavailable" in html


def test_dashboard_action_queue_tracks_trust_level():
    app = load_dashboard_module()
    queue = app.build_action_queue(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), lang="en")
    assert "trust_level" in queue.columns
    assert {"decision", "owner", "eta", "route"} <= set(queue.columns)
    assert queue.loc[0, "trust_level"] == app.TRUST_MODEL_UNAVAILABLE
    html = app.render_action_queue_html(queue, "en")
    assert "Shift action queue" in html
    assert "Model unavailable" in html
    assert "Decision" in html or "Monitor next ingest cycle" in html
    assert "cmd-priority-badge" in html


def test_dashboard_thai_i18n_audit_passes_for_user_facing_strings():
    app = load_dashboard_module()
    assert app.audit_language_strings(app.TEXT, "th") == []


def test_dashboard_thai_dynamic_command_labels_are_localized():
    app = load_dashboard_module()
    queue = app.build_action_queue(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), lang="th")
    queue_html = app.render_action_queue_html(queue, "th")
    assert "ติดตามต่อ" in queue_html
    assert "Monitor" not in queue_html

    snapshot = pd.DataFrame(
        [
            {
                "line_id": "LINE_A",
                "machine_id": "MTR_01",
                "condition_score": 88.0,
                "derived_anomaly_index": 0.12,
            }
        ]
    )
    risk_html = app.render_line_risk_overview(snapshot, "th")
    assert "ต่ำ" in risk_html
    assert "Low" not in risk_html
    assert "cmd-risk-decision-row" in risk_html
    assert "การตัดสินใจ" in risk_html

    alert_html = app.render_alerts_live_html(
        [
            {
                "severity": "Low",
                "time": app.format_alert_time(pd.Timestamp("2026-05-19T01:18:11Z")),
                "machine_id": "MTR_01",
                "title": "แรงสั่น",
                "meta": "LINE_A / ST_01",
                "score": "0.12",
            }
        ],
        "th",
    )
    assert "ต่ำ" in alert_html
    assert "Low" not in alert_html
    assert "01:18:11" in alert_html


def test_chart_preparation_filters_and_downsamples():
    from dashboard.charting import prepare_timeseries

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-05-18", periods=200, freq="min", tz="UTC"),
            "station_id": ["ST-1"] * 100 + ["ST-2"] * 100,
            "value": range(200),
        }
    )
    prepared = prepare_timeseries(df, group_col="station_id", hours=2, max_points=40)
    assert prepared["timestamp"].min() >= df["timestamp"].max() - pd.Timedelta(hours=2)
    assert len(prepared) <= 42


def test_chart_priority_groups_reduce_default_clutter():
    app = load_dashboard_module()
    df = pd.DataFrame(
        {
            "station_id": ["ST-OK"] * 3 + ["ST-RISK"] * 3 + ["ST-DOWN"] * 3,
            "cycle_time_sec": [4.8, 4.9, 4.7, 7.2, 7.4, 7.1, 5.1, 5.0, 5.2],
            "downtime_minutes": [0, 0, 0, 1, 1, 1, 5, 5, 5],
            "defect_rate": [0.005, 0.006, 0.004, 0.02, 0.03, 0.02, 0.01, 0.012, 0.01],
            "station_yield": [0.99, 0.99, 0.99, 0.93, 0.94, 0.93, 0.96, 0.95, 0.96],
        }
    )

    groups = app.priority_groups_for_chart(df, "station_id", limit=2)

    assert set(groups) == {"ST-DOWN", "ST-RISK"}


def test_dashboard_screenshot_script_covers_desktop_and_mobile():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("capture_dashboard_screenshots", root / "scripts" / "capture_dashboard_screenshots.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert {"desktop", "mobile"} <= set(module.VIEWPORTS)
    assert module.VIEWPORTS["desktop"]["width"] >= 1200
    assert module.VIEWPORTS["mobile"]["width"] <= 430
    assert ("Command center", "01_command_center.png") in module.PAGES
    assert ("Line monitoring", "04_line_monitoring.png") in module.PAGES


def test_dashboard_visual_polish_guards():
    root = Path(__file__).resolve().parents[3]
    source = (root / "dashboard" / "app.py").read_text(encoding="utf-8")

    assert 'render_mode="svg"' in source
    assert 'div[data-testid="stPlotlyChart"]' in source
    assert "metric-trust-card" in source
    assert "cmd-kpi-head" in source
    assert "cmd-decision-grid" in source
    assert "cmd-risk-decision-row" in source
    assert ".cmd-action-row {" in source
    assert "@media (max-width: 760px)" in source
    assert "grid-template-columns: 1fr;" in source


def test_portfolio_entrypoint_configures_free_hosting_env(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("streamlit_app_entry", root / "streamlit_app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.delenv("SMOP_PORTFOLIO_MODE", raising=False)
    monkeypatch.delenv("SMOP_AUTO_SEED_DEMO", raising=False)
    monkeypatch.delenv("SMOP_DB_PATH", raising=False)

    module.configure_portfolio_environment()

    assert os.environ["SMOP_PORTFOLIO_MODE"] == "1"
    assert os.environ["SMOP_AUTO_SEED_DEMO"] == "1"
    assert os.environ["SMOP_DB_PATH"].endswith("data/portfolio_demo.db")
    assert str(root) in sys.path


def test_portfolio_bootstrap_seeds_small_demo_database(tmp_path, monkeypatch):
    app = load_dashboard_module()
    db_path = tmp_path / "portfolio_demo.db"

    monkeypatch.setenv("SMOP_AUTO_SEED_DEMO", "1")
    monkeypatch.setenv("SMOP_PORTFOLIO_HOURS", "1")
    monkeypatch.setenv("SMOP_PORTFOLIO_INTERVAL_MINUTES", "30")
    monkeypatch.setenv("SMOP_PORTFOLIO_LINES", "1")
    monkeypatch.setenv("SMOP_PORTFOLIO_MACHINES_PER_LINE", "1")

    from dashboard.portfolio_bootstrap import ensure_portfolio_demo_data, has_dashboard_rows

    summary = ensure_portfolio_demo_data(db_path)

    assert summary["seeded"] is True
    assert has_dashboard_rows(db_path) is True
    with app.sqlite3.connect(db_path) as conn:
        sensor_rows = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
        production_rows = conn.execute("SELECT COUNT(*) FROM production_events").fetchone()[0]
    assert sensor_rows > 0
    assert production_rows > 0

    second = ensure_portfolio_demo_data(db_path)
    assert second["seeded"] is False
    assert second["reason"] == "already_seeded"


def test_dashboard_table_exists_handles_empty_db(temp_db, monkeypatch):
    app = load_dashboard_module()
    monkeypatch.setenv("SMOP_DB_PATH", str(temp_db))
    assert app.table_exists("sensor_readings") is True


def test_dashboard_read_table_returns_dataframe(temp_db, sample_sensor_payload):
    from database import repository
    repository.insert_sensor_reading(sample_sensor_payload, temp_db)
    app = load_dashboard_module()
    # clear cache if Streamlit cache wrapper exposes method
    try:
        app.read_table.clear()
    except Exception:
        pass
    df = app.read_table("sensor_readings")
    assert isinstance(df, pd.DataFrame)
