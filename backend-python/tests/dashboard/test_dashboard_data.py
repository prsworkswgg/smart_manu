from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


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
    assert "Smart Manufacturing AI Operations Report" in report
    assert "Simulated-data" in report


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
