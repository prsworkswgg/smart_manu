"""Streamlit dashboard for the Smart Manufacturing AI Operations Platform.

The dashboard reads operational data from SQLite. It does not use hardcoded placeholder
values. Empty tables are handled with clear fallback messages so the app can be
opened before data collection, training, or prediction has run.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import os
import sys
from html import escape
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.charting import chart_window_options, hours_from_window_label, prepare_timeseries
from dashboard.i18n_audit import audit_language_strings
from dashboard.trust import (
    TRUST_DERIVED,
    TRUST_LIVE,
    TRUST_MODEL_UNAVAILABLE,
    TRUST_NOT_CHECKED,
    TRUST_REPLAY,
    trust_badge_html,
    trust_badges_html,
    trust_label,
)

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

BACKEND_SRC = PROJECT_ROOT / "backend-python" / "src"
if BACKEND_SRC.exists() and str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

try:
    from database import repository as operations_repository
except Exception:  # pragma: no cover - dashboard can still render read-only tables
    operations_repository = None


DEFAULT_LANGUAGE = "en"

LANGUAGE_OPTIONS = {
    "th": "ไทย",
    "en": "English",
    "zh": "中文",
    "ja": "日本語",
}

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Smart Manufacturing Operations Dashboard",
        "hero_label": "Smart manufacturing dashboard",
        "disclaimer": "Real ingestion, API, SQLite, and dashboard workflow running on DEMO data. Values come from stored collector/API records and derived analytics.",
        "site_name": "SMOP Operations Cell",
        "area_name": "Precision electronics line",
        "mode_name": "DEMO data via live ingestion",
        "language_label": "Language",
        "sidebar_title": "SMOP Control",
        "site": "Site",
        "area": "Area",
        "sqlite": "SQLite",
        "refresh_data": "Refresh data",
        "run_order": "Run order",
        "pages": "Pages",
        "page_executive": "Executive overview",
        "page_acquisition": "Data collection",
        "page_line": "Line monitoring",
        "page_equipment": "Equipment health",
        "page_anomaly": "Process alerts",
        "page_quality": "Data quality",
        "page_models": "Model training",
        "page_reports": "Reports and edge setup",
        "na": "N/A",
        "age_seconds": "{value}s ago",
        "age_minutes": "{value}m ago",
        "age_hours": "{value}h ago",
        "age_days": "{value}d ago",
        "waiting_for_data": "Waiting for data",
        "waiting_for_data_note": "No sensor or production events have arrived yet.",
        "timestamp_unavailable": "Timestamp unavailable",
        "timestamp_unavailable_note": "The latest event time could not be read.",
        "live_stream_active": "Live data active",
        "live_stream_active_note": "New records are reaching the system.",
        "stream_delayed": "Data delayed",
        "stream_delayed_note": "Records exist, but the newest event is older than expected.",
        "replay_offline": "Replay data",
        "replay_offline_note": "Data is available for review, but it is not live.",
        "sensor_events": "{value} sensor records",
        "production_events": "{value} production records",
        "model_runs_pill": "{value} model runs",
        "data_freshness": "Data freshness",
        "data_window": "Data window",
        "data_window_caption": "Time range covered by the available records.",
        "date_range": "{start} to {end}",
        "risk_posture": "Current risk",
        "high_signals": "{value} high-priority signals",
        "risk_caption": "High or critical predictions and anomaly alerts.",
        "database": "Database",
        "database_caption": "Local ingestion database used by the operations console.",
        "priority": "Priority",
        "all_lines": "All lines",
        "system": "System",
        "monitor": "Monitor",
        "no_high_priority_action": "No urgent action right now",
        "continue_collecting": "Keep collecting data, refresh model output, and review again at shift handover.",
        "risk_signal": "{risk} risk, health {health}",
        "inspect_asset": "Inspect this asset and confirm the current process condition.",
        "anomaly_alert_signal": "Anomaly score: {score}",
        "review_trend": "Review recent sensor and production trends before shift handover.",
        "data_quality_signal": "Data quality issue: {issue}",
        "verify_channel": "Check the data collection channel before using model output for decisions.",
        "query_failed": "Could not run query: {error}",
        "table_read_failed": "Could not read table {table}: {error}",
        "empty_chart": "No data available for this chart yet.",
        "chart_failed": "Chart could not be shown: {error}",
        "no_data_for_label": "No data available for {label}.",
        "download_csv": "Download {label} CSV",
        "report_title": "Smart Manufacturing AI Operations Report",
        "generated_at": "Generated at",
        "data_policy": "Data profile",
        "shift_summary": "Shift handover summary",
        "operator_queue": "Operator action list",
        "operating_rhythm": "Recommended working rhythm",
        "report_sensor_readings": "Sensor readings",
        "report_production_events": "Production events",
        "report_predictions": "Predictions",
        "report_anomaly_alerts": "Anomaly alerts",
        "report_quality_issues": "Data quality issues",
        "report_model_runs": "Model runs",
        "report_avg_health": "Average health score",
        "report_avg_rul": "Average RUL hours",
        "report_anomaly_count": "Anomaly count",
        "report_latest_prediction": "Latest prediction time",
        "rhythm_1": "Confirm the C# collector and API are receiving records continuously.",
        "rhythm_2": "Review data quality issues before interpreting model output.",
        "rhythm_3": "Rebuild the processed dataset after enough new data has accumulated.",
        "rhythm_4": "Train models and compare registry metrics before using a new artifact.",
        "rhythm_5": "Use the console as operational intelligence from connected records; validate actions through plant procedures before production decisions.",
        "section_note": "Use this page for shift handover: what changed, what needs attention, and what to check next.",
        "page1_header": "1. Executive overview",
        "total_machines": "Total machines",
        "total_lines": "Total lines",
        "critical_machines": "Critical machines",
        "avg_health": "Average health",
        "anomaly_count": "Anomaly count",
        "avg_rul_hours": "Average RUL hours",
        "action_queue": "What needs attention",
        "line_health_summary": "Line health summary",
        "no_predictions_line_health": "No prediction records yet. Train the models and call the prediction endpoints to fill this section.",
        "latest_operational_data": "Latest factory data",
        "latest_sensor_readings": "Latest sensor readings",
        "latest_production_events": "Latest production events",
        "avg_health_by_line": "Average health score by line",
        "page2_header": "2. Data collection",
        "last_received_timestamp": "Last record received",
        "successful_ingestion_count": "Records received",
        "failed_ingestion_count": "Failed records",
        "buffered_records_proxy": "Possible buffered records",
        "delayed_readings": "Delayed readings",
        "collector_status": "Collector status",
        "no_ingested_data": "No collected data found. Start the API, then run the C# collector.",
        "collector_status_proxy": "Collector looks {state}",
        "collector_status_note": "This status is based on the latest SQLite timestamp. A production system should use heartbeat telemetry.",
        "active": "active",
        "stale": "delayed",
        "ingestion_records_per_minute": "Records received per minute",
        "acquisition_logs": "Collection logs",
        "no_acquisition_logs": "No API collection log rows yet. The C# collector writes its own console log.",
        "page3_header": "3. Line monitoring",
        "no_production_events": "No production events yet. Start the C# collector after the API is running.",
        "select_line": "Select line",
        "events": "Events",
        "avg_cycle_time": "Average cycle time",
        "avg_station_yield": "Average station yield",
        "total_downtime_min": "Total downtime minutes",
        "throughput_vs_target": "Throughput compared with target",
        "cycle_time_trend": "Cycle time trend",
        "station_yield_trend": "Station yield trend",
        "reject_defect_rate_trend": "Reject and defect rate trend",
        "micro_stops_downtime": "Micro stops and downtime",
        "micro_stop_count": "Micro stop count",
        "downtime_minutes": "Downtime minutes",
        "page4_header": "4. Equipment health",
        "no_sensor_readings": "No sensor readings available. Start collection first.",
        "select_machine": "Select machine",
        "no_machine_ids": "No machine IDs found in sensor readings.",
        "failure_probability": "Failure probability",
        "rul_hours": "RUL hours",
        "health_score": "Health score",
        "risk_level": "Risk level",
        "sensor_trends": "Sensor trends",
        "sensor_trends_machine": "Sensor trends for {machine}",
        "recommended_action": "Recommended action",
        "no_machine_prediction": "No prediction record for this machine yet. Train models and call the prediction endpoints.",
        "recommended_maintenance_action": "Recommended maintenance action",
        "recommended_maintenance_caption": "Based on failure, RUL, anomaly, and health-score signals.",
        "diagnostic_hint": "Diagnostic note",
        "recent_prediction_history": "Recent prediction history",
        "page5_header": "5. Process alerts",
        "alerts": "Alerts",
        "anomaly_flags": "Anomaly flags",
        "diagnostic_hints": "Diagnostic notes",
        "anomaly_timeline": "Anomaly timeline",
        "anomaly_score_timeline": "Anomaly score over time",
        "anomaly_alert_timeline": "Anomaly alerts over time",
        "no_anomaly_data": "No anomaly predictions or alerts yet. Train models and call /detect/anomaly.",
        "affected_line_station": "Affected line and station",
        "no_alert_rows": "No anomaly alert rows yet.",
        "no_diagnostic_hints": "No diagnostic notes available yet.",
        "page6_header": "6. Data quality",
        "missing_values": "Missing values",
        "duplicate_timestamps": "Duplicate timestamps",
        "stuck_sensor": "Stuck sensor",
        "timestamp_gaps": "Timestamp gaps",
        "sensor_dropout": "Sensor dropout",
        "impossible_values": "Impossible values",
        "no_quality_issues": "No data quality issues recorded yet. Run preprocessing to fill this section.",
        "raw_tables_no_quality": "Raw tables have data, but quality checks have not been saved yet.",
        "issue_counts_by_type": "Issues by type",
        "data_quality_issues_by_type": "Data quality issues by type",
        "issue_severity": "Issue severity",
        "recent_quality_issues": "Recent quality issues",
        "page7_header": "7. Model training",
        "training_command": "Training command",
        "training_note": "Model training runs outside the dashboard. This keeps the operator screen separate from batch and ML jobs.",
        "show_training_reminder": "Show training reminder",
        "training_reminder": "Run the command above in your terminal. The dashboard does not train models inside the web process.",
        "no_model_runs": "No model training rows yet. Run preprocessing, then train the models.",
        "model_runs": "Model runs",
        "metrics": "Metrics",
        "select_model_run_id": "Select model run ID",
        "no_metrics_json": "No metrics JSON is available for this run.",
        "feature_importance": "Feature importance",
        "no_artifact_path": "No artifact path found for the selected model run.",
        "joblib_missing": "joblib is not installed in this environment.",
        "model_artifact_not_found": "Model artifact not found: {path}",
        "no_feature_importance": "This model does not expose feature importance.",
        "top_feature_importance": "Top feature importances",
        "feature_importance_failed": "Could not load feature importance: {error}",
        "page8_header": "8. Reports and edge setup",
        "export_csv": "Export CSV",
        "predictions": "predictions",
        "alerts_label": "alerts",
        "quality_issues_label": "data quality issues",
        "markdown_report": "Markdown report",
        "download_markdown_report": "Download Markdown report",
        "save_report": "Save report to reports/dashboard_report.md",
        "saved_report": "Saved report: {path}",
        "edge_architecture": "Edge setup architecture",
        "limitations": "Deployment boundary",
        "limitations_text": "This console reads the available SQLite, collector, API, model, and quality records. Factory-grade use still requires approved OT/IT integration, security review, historian or PLC integration, verified maintenance labels, process-owner review, and factory acceptance testing.",
    },
    "th": {
        "app_title": "แดชบอร์ดการผลิตอัจฉริยะ",
        "hero_label": "แดชบอร์ดสำหรับติดตามงานผลิต",
        "disclaimer": "ระบบ ingestion, API, SQLite และ dashboard ทำงานจริงบน DEMO data ทุกค่ามาจาก record ที่ collector/API บันทึกไว้และ analytics ที่คำนวณต่อจากข้อมูลนั้น",
        "site_name": "ศูนย์ปฏิบัติการ SMOP",
        "area_name": "ไลน์ผลิตชิ้นส่วนอิเล็กทรอนิกส์",
        "mode_name": "DEMO data ผ่าน live ingestion",
        "language_label": "ภาษา",
        "sidebar_title": "SMOP Control",
        "site": "ไซต์",
        "area": "พื้นที่",
        "sqlite": "SQLite",
        "refresh_data": "รีเฟรชข้อมูล",
        "run_order": "ลำดับการรัน",
        "pages": "หน้า",
        "page_executive": "ภาพรวมผู้ดูแลไลน์",
        "page_acquisition": "การเก็บข้อมูล",
        "page_line": "ติดตามไลน์ผลิต",
        "page_equipment": "สุขภาพเครื่องจักร",
        "page_anomaly": "สัญญาณผิดปกติ",
        "page_quality": "คุณภาพข้อมูล",
        "page_models": "การฝึกโมเดล",
        "page_reports": "รายงานและระบบ Edge",
        "na": "ไม่มีข้อมูล",
        "age_seconds": "{value} วินาทีที่แล้ว",
        "age_minutes": "{value} นาทีที่แล้ว",
        "age_hours": "{value} ชั่วโมงที่แล้ว",
        "age_days": "{value} วันที่แล้ว",
        "waiting_for_data": "รอข้อมูล",
        "waiting_for_data_note": "ยังไม่มีข้อมูลจากเซนเซอร์หรือเหตุการณ์การผลิตเข้ามา",
        "timestamp_unavailable": "อ่านเวลาไม่ได้",
        "timestamp_unavailable_note": "ระบบอ่านเวลาของข้อมูลล่าสุดไม่ได้",
        "live_stream_active": "ข้อมูลกำลังเข้าระบบ",
        "live_stream_active_note": "มีข้อมูลใหม่เข้ามาอย่างต่อเนื่อง",
        "stream_delayed": "ข้อมูลมาช้า",
        "stream_delayed_note": "มีข้อมูลอยู่แล้ว แต่ข้อมูลล่าสุดเก่ากว่าที่คาดไว้",
        "replay_offline": "ข้อมูลย้อนหลัง",
        "replay_offline_note": "มีข้อมูลให้ตรวจดู แต่ไม่ใช่ข้อมูลสด",
        "sensor_events": "ข้อมูลเซนเซอร์ {value} รายการ",
        "production_events": "ข้อมูลการผลิต {value} รายการ",
        "model_runs_pill": "รันโมเดล {value} ครั้ง",
        "data_freshness": "ความสดของข้อมูล",
        "data_window": "ช่วงเวลาของข้อมูล",
        "data_window_caption": "ช่วงเวลาที่ข้อมูลในระบบครอบคลุม",
        "date_range": "{start} ถึง {end}",
        "risk_posture": "ความเสี่ยงตอนนี้",
        "high_signals": "สัญญาณเร่งด่วน {value} รายการ",
        "risk_caption": "ผลทำนายหรือสัญญาณผิดปกติระดับสูงและวิกฤต",
        "database": "ฐานข้อมูล",
        "database_caption": "ฐานข้อมูล ingestion ในเครื่องที่หน้าควบคุมนี้ใช้งาน",
        "priority": "ความสำคัญ",
        "all_lines": "ทุกไลน์",
        "system": "ระบบ",
        "monitor": "ติดตามต่อ",
        "no_high_priority_action": "ตอนนี้ยังไม่มีงานเร่งด่วน",
        "continue_collecting": "เก็บข้อมูลต่อ รีเฟรชผลโมเดล และตรวจอีกครั้งตอนส่งกะ",
        "risk_signal": "ความเสี่ยง {risk}, สุขภาพ {health}",
        "inspect_asset": "ตรวจเครื่องนี้และยืนยันสภาพการผลิตปัจจุบัน",
        "anomaly_alert_signal": "คะแนนความผิดปกติ: {score}",
        "review_trend": "ดูแนวโน้มเซนเซอร์และการผลิตล่าสุดก่อนส่งกะ",
        "data_quality_signal": "ปัญหาคุณภาพข้อมูล: {issue}",
        "verify_channel": "ตรวจช่องทางเก็บข้อมูลก่อนใช้ผลโมเดลตัดสินใจ",
        "query_failed": "รันคำสั่งฐานข้อมูลไม่สำเร็จ: {error}",
        "table_read_failed": "อ่านตาราง {table} ไม่สำเร็จ: {error}",
        "empty_chart": "ยังไม่มีข้อมูลสำหรับกราฟนี้",
        "chart_failed": "แสดงกราฟไม่ได้: {error}",
        "no_data_for_label": "ยังไม่มีข้อมูลสำหรับ {label}",
        "download_csv": "ดาวน์โหลด CSV ของ {label}",
        "report_title": "รายงานระบบ AI สำหรับงานผลิตอัจฉริยะ",
        "generated_at": "สร้างเมื่อ",
        "data_policy": "โปรไฟล์ข้อมูล",
        "shift_summary": "สรุปสำหรับส่งกะ",
        "operator_queue": "รายการงานที่ควรดูต่อ",
        "operating_rhythm": "ลำดับการทำงานที่แนะนำ",
        "report_sensor_readings": "ข้อมูลเซนเซอร์",
        "report_production_events": "ข้อมูลการผลิต",
        "report_predictions": "ผลทำนาย",
        "report_anomaly_alerts": "สัญญาณผิดปกติ",
        "report_quality_issues": "ปัญหาคุณภาพข้อมูล",
        "report_model_runs": "การรันโมเดล",
        "report_avg_health": "คะแนนสุขภาพเฉลี่ย",
        "report_avg_rul": "ชั่วโมง RUL เฉลี่ย",
        "report_anomaly_count": "จำนวนความผิดปกติ",
        "report_latest_prediction": "เวลาผลทำนายล่าสุด",
        "rhythm_1": "ตรวจว่า C# collector และ API รับข้อมูลต่อเนื่อง",
        "rhythm_2": "ดูปัญหาคุณภาพข้อมูลก่อนอ่านผลโมเดล",
        "rhythm_3": "สร้างชุดข้อมูลประมวลผลใหม่เมื่อมีข้อมูลเพิ่มพอ",
        "rhythm_4": "ฝึกโมเดลและเทียบค่าจาก registry ก่อนใช้ artifact ใหม่",
        "rhythm_5": "ใช้หน้าจอนี้เป็นข้อมูล intelligence จาก record ที่เชื่อมเข้าระบบ และยืนยันการตัดสินใจตามขั้นตอนหน้างานก่อนใช้กับการผลิต",
        "section_note": "ใช้หน้านี้ตอนส่งกะ: มีอะไรเปลี่ยนไป อะไรควรดู และควรตรวจอะไรต่อ",
        "page1_header": "1. ภาพรวมผู้ดูแลไลน์",
        "total_machines": "จำนวนเครื่องจักร",
        "total_lines": "จำนวนไลน์",
        "critical_machines": "เครื่องที่เสี่ยงสูง",
        "avg_health": "สุขภาพเฉลี่ย",
        "anomaly_count": "จำนวนความผิดปกติ",
        "avg_rul_hours": "RUL เฉลี่ยเป็นชั่วโมง",
        "action_queue": "สิ่งที่ควรดูตอนนี้",
        "line_health_summary": "สรุปสุขภาพของไลน์",
        "no_predictions_line_health": "ยังไม่มีผลทำนาย ให้ฝึกโมเดลและเรียก prediction endpoint ก่อน",
        "latest_operational_data": "ข้อมูลโรงงานล่าสุด",
        "latest_sensor_readings": "ข้อมูลเซนเซอร์ล่าสุด",
        "latest_production_events": "ข้อมูลการผลิตล่าสุด",
        "avg_health_by_line": "คะแนนสุขภาพเฉลี่ยแยกตามไลน์",
        "page2_header": "2. การเก็บข้อมูล",
        "last_received_timestamp": "ข้อมูลล่าสุดที่รับได้",
        "successful_ingestion_count": "จำนวนข้อมูลที่รับได้",
        "failed_ingestion_count": "ข้อมูลที่ส่งไม่สำเร็จ",
        "buffered_records_proxy": "ข้อมูลที่อาจค้างอยู่",
        "delayed_readings": "ข้อมูลล่าช้า",
        "collector_status": "สถานะตัวเก็บข้อมูล",
        "no_ingested_data": "ยังไม่พบข้อมูล ให้เปิด API แล้วรัน C# collector",
        "collector_status_proxy": "ตัวเก็บข้อมูลดูเหมือน{state}",
        "collector_status_note": "สถานะนี้ดูจากเวลาล่าสุดใน SQLite ระบบใช้งานจริงควรมี heartbeat telemetry",
        "active": "ทำงานอยู่",
        "stale": "ล่าช้า",
        "ingestion_records_per_minute": "จำนวนข้อมูลที่รับได้ต่อนาที",
        "acquisition_logs": "บันทึกการเก็บข้อมูล",
        "no_acquisition_logs": "ยังไม่มีแถว log จาก API ส่วน C# collector มี log ใน console ของตัวเอง",
        "page3_header": "3. ติดตามไลน์ผลิต",
        "no_production_events": "ยังไม่มีเหตุการณ์การผลิต ให้รัน C# collector หลังจากเปิด API",
        "select_line": "เลือกไลน์",
        "events": "จำนวนเหตุการณ์",
        "avg_cycle_time": "cycle time เฉลี่ย",
        "avg_station_yield": "yield เฉลี่ยของสถานี",
        "total_downtime_min": "เวลาหยุดรวมเป็นนาที",
        "throughput_vs_target": "ผลผลิตเทียบกับเป้าหมาย",
        "cycle_time_trend": "แนวโน้ม cycle time",
        "station_yield_trend": "แนวโน้ม yield ของสถานี",
        "reject_defect_rate_trend": "แนวโน้ม reject และ defect rate",
        "micro_stops_downtime": "micro stop และ downtime",
        "micro_stop_count": "จำนวน micro stop",
        "downtime_minutes": "downtime เป็นนาที",
        "page4_header": "4. สุขภาพเครื่องจักร",
        "no_sensor_readings": "ยังไม่มีข้อมูลเซนเซอร์ ให้เริ่มเก็บข้อมูลก่อน",
        "select_machine": "เลือกเครื่องจักร",
        "no_machine_ids": "ไม่พบรหัสเครื่องจักรในข้อมูลเซนเซอร์",
        "failure_probability": "โอกาสเสีย",
        "rul_hours": "RUL เป็นชั่วโมง",
        "health_score": "คะแนนสุขภาพ",
        "risk_level": "ระดับความเสี่ยง",
        "sensor_trends": "แนวโน้มเซนเซอร์",
        "sensor_trends_machine": "แนวโน้มเซนเซอร์ของ {machine}",
        "recommended_action": "สิ่งที่แนะนำให้ทำ",
        "no_machine_prediction": "ยังไม่มีผลทำนายของเครื่องนี้ ให้ฝึกโมเดลและเรียก prediction endpoint",
        "recommended_maintenance_action": "งานบำรุงรักษาที่แนะนำ",
        "recommended_maintenance_caption": "อิงจากสัญญาณ failure, RUL, anomaly และ health score",
        "diagnostic_hint": "บันทึกช่วยวิเคราะห์",
        "recent_prediction_history": "ประวัติผลทำนายล่าสุด",
        "page5_header": "5. สัญญาณผิดปกติ",
        "alerts": "สัญญาณเตือน",
        "anomaly_flags": "จำนวน anomaly flag",
        "diagnostic_hints": "บันทึกช่วยวิเคราะห์",
        "anomaly_timeline": "ไทม์ไลน์ความผิดปกติ",
        "anomaly_score_timeline": "คะแนนความผิดปกติตามเวลา",
        "anomaly_alert_timeline": "สัญญาณผิดปกติตามเวลา",
        "no_anomaly_data": "ยังไม่มีผลทำนายหรือสัญญาณผิดปกติ ให้ฝึกโมเดลและเรียก /detect/anomaly",
        "affected_line_station": "ไลน์และสถานีที่เกี่ยวข้อง",
        "no_alert_rows": "ยังไม่มีแถว anomaly alert",
        "no_diagnostic_hints": "ยังไม่มีบันทึกช่วยวิเคราะห์",
        "page6_header": "6. คุณภาพข้อมูล",
        "missing_values": "ข้อมูลหาย",
        "duplicate_timestamps": "เวลาซ้ำ",
        "stuck_sensor": "เซนเซอร์ค้าง",
        "timestamp_gaps": "ช่วงเวลาขาด",
        "sensor_dropout": "เซนเซอร์หลุด",
        "impossible_values": "ค่าที่เป็นไปไม่ได้",
        "no_quality_issues": "ยังไม่มีปัญหาคุณภาพข้อมูล ให้รัน preprocessing เพื่อสร้างข้อมูลส่วนนี้",
        "raw_tables_no_quality": "ตารางดิบมีข้อมูลแล้ว แต่ยังไม่ได้บันทึกผลตรวจคุณภาพ",
        "issue_counts_by_type": "จำนวนปัญหาแยกตามประเภท",
        "data_quality_issues_by_type": "ปัญหาคุณภาพข้อมูลแยกตามประเภท",
        "issue_severity": "ระดับความรุนแรงของปัญหา",
        "recent_quality_issues": "ปัญหาคุณภาพข้อมูลล่าสุด",
        "page7_header": "7. การฝึกโมเดล",
        "training_command": "คำสั่งฝึกโมเดล",
        "training_note": "การฝึกโมเดลอยู่นอกหน้า dashboard เพื่อแยกหน้าจอผู้ใช้ออกจาก batch job และงาน ML",
        "show_training_reminder": "แสดงคำเตือนการฝึกโมเดล",
        "training_reminder": "รันคำสั่งด้านบนใน terminal หน้า dashboard จะไม่ฝึกโมเดลใน web process",
        "no_model_runs": "ยังไม่มีประวัติการฝึกโมเดล ให้รัน preprocessing แล้วฝึกโมเดล",
        "model_runs": "ประวัติการรันโมเดล",
        "metrics": "ค่าประเมินโมเดล",
        "select_model_run_id": "เลือก ID การรันโมเดล",
        "no_metrics_json": "รอบนี้ยังไม่มี metrics JSON",
        "feature_importance": "ความสำคัญของ feature",
        "no_artifact_path": "ไม่พบ artifact path ของโมเดลที่เลือก",
        "joblib_missing": "สภาพแวดล้อมนี้ยังไม่มี joblib",
        "model_artifact_not_found": "ไม่พบ artifact ของโมเดล: {path}",
        "no_feature_importance": "โมเดลนี้ไม่มีค่า feature importance ให้แสดง",
        "top_feature_importance": "feature ที่สำคัญที่สุด",
        "feature_importance_failed": "โหลด feature importance ไม่สำเร็จ: {error}",
        "page8_header": "8. รายงานและระบบ Edge",
        "export_csv": "ส่งออก CSV",
        "predictions": "ผลทำนาย",
        "alerts_label": "สัญญาณเตือน",
        "quality_issues_label": "ปัญหาคุณภาพข้อมูล",
        "markdown_report": "รายงาน Markdown",
        "download_markdown_report": "ดาวน์โหลดรายงาน Markdown",
        "save_report": "บันทึกรายงานไปที่ reports/dashboard_report.md",
        "saved_report": "บันทึกรายงานแล้ว: {path}",
        "edge_architecture": "โครงสร้างระบบ Edge",
        "limitations": "ขอบเขตการใช้งาน",
        "limitations_text": "หน้าจอนี้อ่านข้อมูลจาก SQLite, collector, API, model registry และ data quality records ที่มีอยู่ การใช้งานระดับโรงงานจริงยังต้องมี OT/IT integration ที่อนุมัติแล้ว, security review, historian หรือ PLC integration, maintenance label ที่ยืนยันได้, การตรวจจากเจ้าของกระบวนการ และ factory acceptance testing",
    },
}

TEXT["zh"] = {
    **TEXT["en"],
    "app_title": "智能制造运营仪表板",
    "hero_label": "制造现场运营看板",
    "disclaimer": "真实 ingestion、API、SQLite 和 dashboard 流程正在使用 DEMO data。所有数值来自已存储的 collector/API 记录和派生分析。",
    "site_name": "SMOP 运营单元",
    "area_name": "精密电子产线",
    "mode_name": "DEMO data 实时接入",
    "language_label": "语言",
    "site": "站点",
    "area": "区域",
    "refresh_data": "刷新数据",
    "run_order": "运行顺序",
    "pages": "页面",
    "page_executive": "管理总览",
    "page_acquisition": "数据采集",
    "page_line": "产线监控",
    "page_equipment": "设备健康",
    "page_anomaly": "异常信号",
    "page_quality": "数据质量",
    "page_models": "模型训练",
    "page_reports": "报告与边缘部署",
    "na": "暂无数据",
    "age_seconds": "{value} 秒前",
    "age_minutes": "{value} 分钟前",
    "age_hours": "{value} 小时前",
    "age_days": "{value} 天前",
    "live_stream_active": "数据正在进入系统",
    "live_stream_active_note": "系统正在收到新记录。",
    "waiting_for_data": "等待数据",
    "waiting_for_data_note": "还没有传感器或生产事件进入系统。",
    "stream_delayed": "数据有延迟",
    "stream_delayed_note": "系统有记录，但最新事件早于预期。",
    "replay_offline": "回放数据",
    "replay_offline_note": "可以查看数据，但它不是实时流。",
    "sensor_events": "{value} 条传感器记录",
    "production_events": "{value} 条生产记录",
    "model_runs_pill": "{value} 次模型运行",
    "data_freshness": "数据新鲜度",
    "data_window": "数据时间范围",
    "data_window_caption": "当前记录覆盖的时间范围。",
    "date_range": "{start} 至 {end}",
    "risk_posture": "当前风险",
    "high_signals": "{value} 个高优先级信号",
    "risk_caption": "高或严重级别的预测和异常警报。",
    "database": "数据库",
    "database_caption": "运营控制台使用的本地接入数据库。",
    "priority": "优先级",
    "all_lines": "所有产线",
    "system": "系统",
    "monitor": "继续观察",
    "no_high_priority_action": "当前没有紧急事项",
    "continue_collecting": "继续收集数据，刷新模型输出，并在交接班时复查。",
    "section_note": "交接班时使用此页：查看变化、需要关注的内容和下一步检查。",
    "page1_header": "1. 管理总览",
    "total_machines": "设备总数",
    "total_lines": "产线总数",
    "critical_machines": "高风险设备",
    "avg_health": "平均健康分",
    "anomaly_count": "异常数量",
    "avg_rul_hours": "平均 RUL 小时",
    "action_queue": "当前需要关注",
    "line_health_summary": "产线健康摘要",
    "latest_operational_data": "最新工厂数据",
    "latest_sensor_readings": "最新传感器读数",
    "latest_production_events": "最新生产事件",
    "page2_header": "2. 数据采集",
    "collector_status": "采集器状态",
    "page3_header": "3. 产线监控",
    "select_line": "选择产线",
    "page4_header": "4. 设备健康",
    "select_machine": "选择设备",
    "recommended_action": "建议操作",
    "page5_header": "5. 异常信号",
    "page6_header": "6. 数据质量",
    "page7_header": "7. 模型训练",
    "training_command": "训练命令",
    "page8_header": "8. 报告与边缘部署",
    "limitations": "部署边界",
    "limitations_text": "本控制台读取可用的 SQLite、collector、API、模型和数据质量记录。工厂级使用仍需要获批的 OT/IT 集成、安全审查、historian 或 PLC 集成、已验证维护标签、流程负责人审核和工厂验收测试。",
}

TEXT["ja"] = {
    **TEXT["en"],
    "app_title": "スマート製造オペレーションダッシュボード",
    "hero_label": "製造現場の運用ダッシュボード",
    "disclaimer": "実際の ingestion、API、SQLite、dashboard ワークフローが DEMO data 上で動作しています。値は保存済み collector/API レコードと派生分析から来ています。",
    "site_name": "SMOP デモ工場",
    "area_name": "精密電子部品ライン",
    "mode_name": "ライブ取り込みデータベース",
    "language_label": "言語",
    "site": "サイト",
    "area": "エリア",
    "refresh_data": "データを更新",
    "run_order": "実行順",
    "pages": "ページ",
    "page_executive": "管理者向け概要",
    "page_acquisition": "データ収集",
    "page_line": "ライン監視",
    "page_equipment": "設備の状態",
    "page_anomaly": "異常シグナル",
    "page_quality": "データ品質",
    "page_models": "モデル学習",
    "page_reports": "レポートとエッジ設定",
    "na": "データなし",
    "age_seconds": "{value} 秒前",
    "age_minutes": "{value} 分前",
    "age_hours": "{value} 時間前",
    "age_days": "{value} 日前",
    "live_stream_active": "データ受信中",
    "live_stream_active_note": "新しい記録がシステムに届いています。",
    "waiting_for_data": "データ待ち",
    "waiting_for_data_note": "センサーまたは生産イベントがまだ届いていません。",
    "stream_delayed": "データが遅れています",
    "stream_delayed_note": "記録はありますが、最新イベントが想定より古くなっています。",
    "replay_offline": "再生データ",
    "replay_offline_note": "確認できるデータはありますが、ライブではありません。",
    "sensor_events": "センサー記録 {value} 件",
    "production_events": "生産記録 {value} 件",
    "model_runs_pill": "モデル実行 {value} 回",
    "data_freshness": "データの新しさ",
    "data_window": "データの期間",
    "data_window_caption": "利用できる記録がカバーする期間です。",
    "date_range": "{start} から {end}",
    "risk_posture": "現在のリスク",
    "high_signals": "高優先度シグナル {value} 件",
    "risk_caption": "高または重大な予測と異常アラート。",
    "database": "データベース",
    "database_caption": "このデモで使うローカルデータベースです。",
    "priority": "優先度",
    "all_lines": "すべてのライン",
    "system": "システム",
    "monitor": "監視継続",
    "no_high_priority_action": "今すぐ対応する緊急事項はありません",
    "continue_collecting": "データ収集を続け、モデル出力を更新し、交代時にもう一度確認してください。",
    "section_note": "交代時に使うページです。変化、注意点、次に確認する内容をまとめます。",
    "page1_header": "1. 管理者向け概要",
    "total_machines": "設備数",
    "total_lines": "ライン数",
    "critical_machines": "高リスク設備",
    "avg_health": "平均健康スコア",
    "anomaly_count": "異常数",
    "avg_rul_hours": "平均 RUL 時間",
    "action_queue": "今見るべきこと",
    "line_health_summary": "ライン状態のまとめ",
    "latest_operational_data": "最新の工場データ",
    "latest_sensor_readings": "最新センサー読取",
    "latest_production_events": "最新生産イベント",
    "page2_header": "2. データ収集",
    "collector_status": "収集プログラムの状態",
    "page3_header": "3. ライン監視",
    "select_line": "ラインを選択",
    "page4_header": "4. 設備の状態",
    "select_machine": "設備を選択",
    "recommended_action": "推奨アクション",
    "page5_header": "5. 異常シグナル",
    "page6_header": "6. データ品質",
    "page7_header": "7. モデル学習",
    "training_command": "学習コマンド",
    "page8_header": "8. レポートとエッジ設定",
    "limitations": "このデモの制限",
    "limitations_text": "このコンソールは利用可能な SQLite、collector、API、モデル、データ品質レコードを読み取ります。工場レベルで使うには、承認済み OT/IT 連携、セキュリティレビュー、historian または PLC 連携、検証済み保全ラベル、工程責任者レビュー、工場受入試験が必要です。",
}

TEXT["en"]["edge_architecture_text"] = """```text
Factory floor or edge PC
  C# SensorCollector
    -> reads machine and station settings
    -> creates or receives sensor and production events
    -> keeps JSONL buffer files when the network or API is unavailable
    -> sends records to FastAPI over HTTP

Local analytics node
  FastAPI ingestion and inference
    -> checks incoming records
    -> writes SQLite
    -> loads model artifacts
    -> returns failure, RUL, and anomaly predictions

Operations dashboard
  Streamlit
    -> reads SQLite and API data
    -> shows health, alerts, data quality, and model history
    -> exports CSV and Markdown reports
```"""

TEXT["th"].update(
    {
        "sidebar_title": "แผงควบคุม SMOP",
        "sqlite": "ตำแหน่ง SQLite",
        "edge_architecture_text": """```text
พื้นโรงงานหรือ Edge PC
  C# SensorCollector
    -> อ่านค่าตั้งต้นของเครื่องจักรและสถานี
    -> สร้างหรือรับข้อมูลเซนเซอร์และเหตุการณ์การผลิต
    -> เก็บไฟล์ JSONL สำรองเมื่อเครือข่ายหรือ API ใช้งานไม่ได้
    -> ส่งข้อมูลเข้า FastAPI ผ่าน HTTP

เครื่องวิเคราะห์ข้อมูลในพื้นที่
  FastAPI สำหรับรับข้อมูลและทำนายผล
    -> ตรวจข้อมูลที่เข้ามา
    -> เขียนข้อมูลลง SQLite
    -> โหลด model artifact
    -> ส่งผล failure, RUL และ anomaly กลับไป

Dashboard สำหรับทีมปฏิบัติการ
  Streamlit
    -> อ่านข้อมูลจาก SQLite และ API
    -> แสดงสุขภาพเครื่องจักร สัญญาณเตือน คุณภาพข้อมูล และประวัติโมเดล
    -> ส่งออก CSV และรายงาน Markdown
```""",
    }
)

TEXT["zh"].update(
    {
        "sidebar_title": "SMOP 控制台",
        "sqlite": "SQLite 路径",
        "timestamp_unavailable": "无法读取时间",
        "timestamp_unavailable_note": "无法解析最新事件时间。",
        "risk_signal": "{risk} 风险，健康分 {health}",
        "inspect_asset": "检查该设备，并确认当前工艺状态。",
        "anomaly_alert_signal": "异常分数：{score}",
        "review_trend": "交接班前查看最近的传感器和生产趋势。",
        "data_quality_signal": "数据质量问题：{issue}",
        "verify_channel": "使用模型输出前，先检查数据采集通道。",
        "query_failed": "数据库查询失败：{error}",
        "table_read_failed": "无法读取表 {table}：{error}",
        "empty_chart": "此图表暂时没有数据。",
        "chart_failed": "图表无法显示：{error}",
        "no_data_for_label": "{label} 暂无数据。",
        "download_csv": "下载 {label} CSV",
        "report_title": "智能制造 AI 运营报告",
        "generated_at": "生成时间",
        "data_policy": "数据配置",
        "shift_summary": "交接班摘要",
        "operator_queue": "待关注事项",
        "operating_rhythm": "建议工作节奏",
        "report_sensor_readings": "传感器记录",
        "report_production_events": "生产事件",
        "report_predictions": "预测结果",
        "report_anomaly_alerts": "异常警报",
        "report_quality_issues": "数据质量问题",
        "report_model_runs": "模型运行",
        "report_avg_health": "平均健康分",
        "report_avg_rul": "平均 RUL 小时",
        "report_anomaly_count": "异常数量",
        "report_latest_prediction": "最新预测时间",
        "rhythm_1": "确认 C# collector 和 API 正在持续接收记录。",
        "rhythm_2": "解释模型输出前，先查看数据质量问题。",
        "rhythm_3": "积累足够新数据后，重新生成处理后的数据集。",
        "rhythm_4": "训练模型，并比较 registry 指标后再使用新 artifact。",
        "rhythm_5": "把所有输出视为模拟原型证据，不要当作已验证的生产建议。",
        "no_predictions_line_health": "还没有预测记录。先训练模型并调用预测接口，才能填充此区域。",
        "avg_health_by_line": "各产线平均健康分",
        "last_received_timestamp": "最近收到的记录",
        "successful_ingestion_count": "已接收记录",
        "failed_ingestion_count": "失败记录",
        "buffered_records_proxy": "可能缓存的记录",
        "delayed_readings": "延迟读数",
        "no_ingested_data": "还没有采集到数据。先启动 API，再运行 C# collector。",
        "collector_status_proxy": "采集器看起来{state}",
        "collector_status_note": "此状态基于 SQLite 的最新时间戳。生产系统应使用心跳遥测。",
        "active": "正常",
        "stale": "延迟",
        "ingestion_records_per_minute": "每分钟接收记录数",
        "acquisition_logs": "采集日志",
        "no_acquisition_logs": "还没有 API 采集日志。C# collector 会在自己的控制台输出日志。",
        "no_production_events": "还没有生产事件。API 运行后再启动 C# collector。",
        "events": "事件数",
        "avg_cycle_time": "平均周期时间",
        "avg_station_yield": "平均工位良率",
        "total_downtime_min": "总停机分钟",
        "throughput_vs_target": "产量与目标对比",
        "cycle_time_trend": "周期时间趋势",
        "station_yield_trend": "工位良率趋势",
        "reject_defect_rate_trend": "拒收与缺陷率趋势",
        "micro_stops_downtime": "微停与停机",
        "micro_stop_count": "微停次数",
        "downtime_minutes": "停机分钟",
        "no_sensor_readings": "还没有传感器读数。请先启动采集。",
        "no_machine_ids": "传感器读数中没有设备 ID。",
        "failure_probability": "故障概率",
        "rul_hours": "RUL 小时",
        "health_score": "健康分",
        "risk_level": "风险等级",
        "sensor_trends": "传感器趋势",
        "sensor_trends_machine": "{machine} 的传感器趋势",
        "no_machine_prediction": "此设备还没有预测记录。请训练模型并调用预测接口。",
        "recommended_maintenance_action": "建议维护操作",
        "recommended_maintenance_caption": "基于故障、RUL、异常和健康分信号。",
        "diagnostic_hint": "诊断说明",
        "recent_prediction_history": "最近预测历史",
        "alerts": "警报",
        "anomaly_flags": "异常标记",
        "diagnostic_hints": "诊断说明",
        "anomaly_timeline": "异常时间线",
        "anomaly_score_timeline": "异常分数随时间变化",
        "anomaly_alert_timeline": "异常警报随时间变化",
        "no_anomaly_data": "还没有异常预测或警报。请训练模型并调用 /detect/anomaly。",
        "affected_line_station": "受影响的产线和工位",
        "no_alert_rows": "还没有异常警报记录。",
        "no_diagnostic_hints": "还没有诊断说明。",
        "missing_values": "缺失值",
        "duplicate_timestamps": "重复时间戳",
        "stuck_sensor": "传感器卡住",
        "timestamp_gaps": "时间缺口",
        "sensor_dropout": "传感器掉线",
        "impossible_values": "不可能值",
        "no_quality_issues": "还没有记录数据质量问题。运行 preprocessing 后会生成此部分。",
        "raw_tables_no_quality": "原始表已有数据，但质量检查结果还没有保存。",
        "issue_counts_by_type": "按类型统计问题",
        "data_quality_issues_by_type": "按类型统计数据质量问题",
        "issue_severity": "问题严重级别",
        "recent_quality_issues": "最近数据质量问题",
        "training_note": "模型训练在 dashboard 外运行，这样操作界面不会和批处理或 ML 作业混在一起。",
        "show_training_reminder": "显示训练提醒",
        "training_reminder": "请在终端运行上面的命令。dashboard 不会在网页进程里训练模型。",
        "no_model_runs": "还没有模型训练记录。请先运行 preprocessing，再训练模型。",
        "model_runs": "模型运行记录",
        "metrics": "评估指标",
        "select_model_run_id": "选择模型运行 ID",
        "no_metrics_json": "此运行没有 metrics JSON。",
        "feature_importance": "特征重要性",
        "no_artifact_path": "所选模型运行没有 artifact path。",
        "joblib_missing": "当前环境未安装 joblib。",
        "model_artifact_not_found": "找不到模型 artifact：{path}",
        "no_feature_importance": "此模型没有可显示的特征重要性。",
        "top_feature_importance": "最重要的特征",
        "feature_importance_failed": "无法加载特征重要性：{error}",
        "export_csv": "导出 CSV",
        "predictions": "预测结果",
        "alerts_label": "警报",
        "quality_issues_label": "数据质量问题",
        "markdown_report": "Markdown 报告",
        "download_markdown_report": "下载 Markdown 报告",
        "save_report": "保存报告到 reports/dashboard_report.md",
        "saved_report": "报告已保存：{path}",
        "edge_architecture": "边缘部署结构",
        "edge_architecture_text": """```text
工厂现场或 Edge PC
  C# SensorCollector
    -> 读取设备和工位设置
    -> 创建或接收传感器与生产事件
    -> 网络或 API 不可用时保留 JSONL 缓冲文件
    -> 通过 HTTP 发送记录到 FastAPI

本地分析节点
  FastAPI 数据接收和推理
    -> 检查传入记录
    -> 写入 SQLite
    -> 加载模型 artifact
    -> 返回故障、RUL 和异常预测

运营 dashboard
  Streamlit
    -> 读取 SQLite 和 API 数据
    -> 显示健康、警报、数据质量和模型历史
    -> 导出 CSV 和 Markdown 报告
```""",
    }
)

TEXT["ja"].update(
    {
        "sidebar_title": "SMOP コントロール",
        "sqlite": "SQLite パス",
        "timestamp_unavailable": "時刻を読めません",
        "timestamp_unavailable_note": "最新イベント時刻を解析できません。",
        "risk_signal": "{risk} リスク、健康スコア {health}",
        "inspect_asset": "この設備を確認し、現在の工程状態を見てください。",
        "anomaly_alert_signal": "異常スコア：{score}",
        "review_trend": "交代前に最近のセンサーと生産の傾向を確認してください。",
        "data_quality_signal": "データ品質の問題：{issue}",
        "verify_channel": "モデル出力を使う前に、データ収集経路を確認してください。",
        "query_failed": "データベースクエリに失敗しました：{error}",
        "table_read_failed": "テーブル {table} を読めません：{error}",
        "empty_chart": "このグラフに表示するデータはまだありません。",
        "chart_failed": "グラフを表示できません：{error}",
        "no_data_for_label": "{label} のデータはまだありません。",
        "download_csv": "{label} CSV をダウンロード",
        "report_title": "スマート製造 AI オペレーションレポート",
        "generated_at": "作成時刻",
        "data_policy": "データプロファイル",
        "shift_summary": "交代時サマリー",
        "operator_queue": "確認すべき項目",
        "operating_rhythm": "推奨する作業手順",
        "report_sensor_readings": "センサー記録",
        "report_production_events": "生産イベント",
        "report_predictions": "予測結果",
        "report_anomaly_alerts": "異常アラート",
        "report_quality_issues": "データ品質の問題",
        "report_model_runs": "モデル実行",
        "report_avg_health": "平均健康スコア",
        "report_avg_rul": "平均 RUL 時間",
        "report_anomaly_count": "異常数",
        "report_latest_prediction": "最新予測時刻",
        "rhythm_1": "C# collector と API が継続して記録を受信していることを確認します。",
        "rhythm_2": "モデル出力を読む前に、データ品質の問題を確認します。",
        "rhythm_3": "十分な新しいデータがたまったら、処理済みデータセットを作り直します。",
        "rhythm_4": "新しい artifact を使う前に、モデルを学習し registry の指標を比較します。",
        "rhythm_5": "接続済みレコードからの運用インテリジェンスとして利用し、生産判断の前に現場手順で確認します。",
        "no_predictions_line_health": "予測記録はまだありません。モデルを学習し、予測エンドポイントを呼び出すと表示されます。",
        "avg_health_by_line": "ライン別の平均健康スコア",
        "last_received_timestamp": "最後に受信した記録",
        "successful_ingestion_count": "受信済み記録",
        "failed_ingestion_count": "失敗した記録",
        "buffered_records_proxy": "バッファの可能性がある記録",
        "delayed_readings": "遅延した読取",
        "no_ingested_data": "収集データがまだありません。API を起動してから C# collector を実行してください。",
        "collector_status_proxy": "収集プログラムは{state}ようです",
        "collector_status_note": "この状態は SQLite の最新時刻で判断しています。本番では heartbeat telemetry が必要です。",
        "active": "稼働中",
        "stale": "遅延中",
        "ingestion_records_per_minute": "1分あたりの受信記録数",
        "acquisition_logs": "収集ログ",
        "no_acquisition_logs": "API の収集ログ行はまだありません。C# collector は自分のコンソールにログを出します。",
        "no_production_events": "生産イベントはまだありません。API を起動してから C# collector を実行してください。",
        "events": "イベント数",
        "avg_cycle_time": "平均サイクル時間",
        "avg_station_yield": "平均ステーション歩留まり",
        "total_downtime_min": "合計停止分",
        "throughput_vs_target": "スループットと目標の比較",
        "cycle_time_trend": "サイクル時間の傾向",
        "station_yield_trend": "ステーション歩留まりの傾向",
        "reject_defect_rate_trend": "リジェクトと欠陥率の傾向",
        "micro_stops_downtime": "短時間停止と停止時間",
        "micro_stop_count": "短時間停止回数",
        "downtime_minutes": "停止時間分",
        "no_sensor_readings": "センサー読取はまだありません。先に収集を開始してください。",
        "no_machine_ids": "センサー読取に設備 ID がありません。",
        "failure_probability": "故障確率",
        "rul_hours": "RUL 時間",
        "health_score": "健康スコア",
        "risk_level": "リスクレベル",
        "sensor_trends": "センサー傾向",
        "sensor_trends_machine": "{machine} のセンサー傾向",
        "no_machine_prediction": "この設備の予測記録はまだありません。モデルを学習し、予測エンドポイントを呼び出してください。",
        "recommended_maintenance_action": "推奨保全アクション",
        "recommended_maintenance_caption": "故障、RUL、異常、健康スコアのシグナルに基づきます。",
        "diagnostic_hint": "診断メモ",
        "recent_prediction_history": "最近の予測履歴",
        "alerts": "アラート",
        "anomaly_flags": "異常フラグ",
        "diagnostic_hints": "診断メモ",
        "anomaly_timeline": "異常タイムライン",
        "anomaly_score_timeline": "異常スコアの推移",
        "anomaly_alert_timeline": "異常アラートの推移",
        "no_anomaly_data": "異常予測またはアラートはまだありません。モデルを学習し /detect/anomaly を呼び出してください。",
        "affected_line_station": "影響を受けたラインとステーション",
        "no_alert_rows": "異常アラート行はまだありません。",
        "no_diagnostic_hints": "診断メモはまだありません。",
        "missing_values": "欠損値",
        "duplicate_timestamps": "重複時刻",
        "stuck_sensor": "センサー固定",
        "timestamp_gaps": "時刻の欠落",
        "sensor_dropout": "センサー脱落",
        "impossible_values": "あり得ない値",
        "no_quality_issues": "データ品質の問題はまだ記録されていません。preprocessing を実行すると表示されます。",
        "raw_tables_no_quality": "生データ表にはデータがありますが、品質チェック結果はまだ保存されていません。",
        "issue_counts_by_type": "タイプ別の問題数",
        "data_quality_issues_by_type": "タイプ別データ品質問題",
        "issue_severity": "問題の重大度",
        "recent_quality_issues": "最近のデータ品質問題",
        "training_note": "モデル学習は dashboard の外で実行します。操作画面を batch や ML ジョブから分けるためです。",
        "show_training_reminder": "学習リマインダーを表示",
        "training_reminder": "上のコマンドを terminal で実行してください。dashboard は Web プロセス内でモデルを学習しません。",
        "no_model_runs": "モデル学習記録はまだありません。preprocessing の後にモデルを学習してください。",
        "model_runs": "モデル実行履歴",
        "metrics": "評価指標",
        "select_model_run_id": "モデル実行 ID を選択",
        "no_metrics_json": "この実行には metrics JSON がありません。",
        "feature_importance": "特徴量重要度",
        "no_artifact_path": "選択したモデル実行に artifact path がありません。",
        "joblib_missing": "この環境には joblib がインストールされていません。",
        "model_artifact_not_found": "モデル artifact が見つかりません：{path}",
        "no_feature_importance": "このモデルには表示できる特徴量重要度がありません。",
        "top_feature_importance": "重要な特徴量",
        "feature_importance_failed": "特徴量重要度を読み込めません：{error}",
        "export_csv": "CSV をエクスポート",
        "predictions": "予測結果",
        "alerts_label": "アラート",
        "quality_issues_label": "データ品質の問題",
        "markdown_report": "Markdown レポート",
        "download_markdown_report": "Markdown レポートをダウンロード",
        "save_report": "reports/dashboard_report.md に保存",
        "saved_report": "レポートを保存しました：{path}",
        "edge_architecture": "エッジ設定の構成",
        "edge_architecture_text": """```text
工場現場または Edge PC
  C# SensorCollector
    -> 設備とステーションの設定を読む
    -> センサーと生産イベントを作成または受信する
    -> ネットワークまたは API が使えない時は JSONL バッファを保持する
    -> HTTP で FastAPI に記録を送る

ローカル分析ノード
  FastAPI の受信と推論
    -> 入力記録を確認する
    -> SQLite に書き込む
    -> モデル artifact を読み込む
    -> 故障、RUL、異常の予測を返す

運用 dashboard
  Streamlit
    -> SQLite と API のデータを読む
    -> 状態、アラート、データ品質、モデル履歴を表示する
    -> CSV と Markdown レポートを出力する
```""",
    }
)

TEXT["en"].update(
    {
        "app_title": "Factory Intelligence Operations Console",
        "hero_label": "Live manufacturing intelligence",
        "disclaimer": "Real ingestion, API, SQLite, and dashboard workflow running on DEMO data. Values come from stored collector/API records and derived analytics.",
        "site_name": "SMOP Operations Cell",
        "mode_name": "DEMO data via live ingestion",
        "database_caption": "Local ingestion database used by the operations console.",
        "page_executive": "Command center",
        "page_workflow": "Operations workflow",
        "page_equipment": "Machine investigation",
        "page_anomaly": "Anomaly investigation",
        "page1_header": "1. Command center",
        "page_workflow_header": "Operations workflow system",
        "page4_header": "4. Machine investigation",
        "page5_header": "5. Anomaly investigation",
        "section_note": "Start with the command view for the plant picture, then open a machine investigation when a signal deserves a deeper read.",
        "report_title": "Factory Intelligence Operations Report",
        "rhythm_5": "Use the console as operational intelligence from connected records; validate actions through plant procedures before production decisions.",
        "limitations": "Deployment boundary",
        "limitations_text": "This console reads the available SQLite, collector, API, model, and quality records. Factory-grade use still requires approved OT/IT integration, security review, historian or PLC integration, verified maintenance labels, process-owner review, and factory acceptance testing.",
        "data_origin_title": "Data provenance",
        "data_origin_body": "Every value on this screen is read from the local ingestion database, model registry, or derived from recent DEMO data records. No dashboard value is hardcoded.",
        "data_origin_scope": "Input source: DEMO data written by the collector/API into SQLite. Production use requires real machine integration and owner sign-off.",
        "plant_pulse": "Plant pulse",
        "machine_health_map": "Machine health map",
        "machine_health_map_caption": "Derived from latest machine records and model health when available.",
        "machine_matrix_empty": "No machine records are available yet.",
        "investigation_panel": "Machine investigation panel",
        "investigation_panel_caption": "Select any machine to see the live record, derived condition score, signal drivers, and recent event trail.",
        "select_machine_for_deep_dive": "Select machine for deep dive",
        "condition_score": "Condition score",
        "derived_anomaly_index": "Derived anomaly index",
        "dominant_signal": "Dominant signal",
        "latest_event": "Latest event",
        "operating_context": "Operating context",
        "line_station": "Line / station",
        "source_records": "Source records",
        "sensor_record_count": "{value} sensor rows",
        "production_record_count": "{value} production rows",
        "investigation_note": "This is an engineering triage view: confirm the signal pattern, compare production context, and decide whether model inference or maintenance review is needed.",
        "machine_signal_trend": "Machine signal trend",
        "machine_signal_trend_caption": "Recent sensor values for the selected machine.",
        "anomaly_timeline_derived": "Condition drift timeline",
        "anomaly_timeline_caption": "When model alerts are unavailable, the console derives a transparent anomaly index from vibration, wear, current, torque, and temperature records.",
        "risk_normal": "Stable",
        "risk_low": "Low",
        "risk_elevated": "Elevated",
        "risk_high": "High",
        "risk_critical": "Critical",
        "signal_vibration": "Vibration",
        "signal_tool_wear": "Tool wear",
        "signal_temperature": "Process temperature",
        "signal_motor_current": "Motor current",
        "signal_torque": "Torque",
        "signal_balanced": "Balanced signal",
        "no_machine_stream": "No machine stream is available for the selected asset.",
        "detail_tab_overview": "Overview",
        "detail_tab_signals": "Signals",
        "detail_tab_events": "Event trail",
        "detail_tab_context": "Context",
        "latest_sensor_record": "Latest sensor record",
        "latest_production_record": "Latest production record",
        "recent_machine_records": "Recent machine records",
        "showing_database_records": "Showing live SQLite records from the active database.",
        "model_status_body": "Model registry is empty. The console still shows live condition analytics from sensor and production records.",
        "derived_anomaly_watchlist": "Derived anomaly watchlist",
        "derived_anomaly_watchlist_caption": "Ranked from sensor records when model alerts are unavailable.",
        "no_derived_anomaly_records": "No derived anomaly records are available from the current sensor stream.",
        "model_alerts_unavailable": "Model alerts are not available yet, so this view is using a transparent sensor-derived anomaly index.",
        "derived_diagnostic_hint": "Sensor-derived triage note",
        "derived_recommended_action": "Review the selected machine trend, compare production context, and confirm whether maintenance or model inference is required.",
        "command_center_title": "OPERATIONS COMMAND CENTER",
        "live_label": "LIVE",
        "last_update": "Last update",
        "shift_label": "Shift A",
        "plant_label": "Plant 1",
        "overview_nav_caption": "Command Center",
        "data_source_title": "DATA SOURCE",
        "all_systems_operational": "All systems operational",
        "ingestion_api": "Ingestion API",
        "database_service": "Database",
        "collector_agents": "Collector agents",
        "model_service": "Model service",
        "view_data_pipeline": "View Data Pipeline",
        "model_run_count": "{value} runs",
        "record_count": "{value} records",
        "overall_equipment_effectiveness": "Overall equipment effectiveness",
        "active_lines": "Active lines",
        "machines_label": "Machines",
        "anomalies_24h": "Anomalies (24h)",
        "mttr_24h": "MTTR (24h)",
        "next_maintenance": "Next maintenance",
        "due_within_72": "Due within 72 hours",
        "running_label": "Running",
        "critical_label": "critical",
        "warning_label": "warning",
        "line_risk_overview": "Line risk overview",
        "risk_score_weighted": "Risk score (weighted)",
        "alerts_live": "Alerts (live)",
        "view_all_alerts": "View all alerts",
        "event_distribution_24h": "Event distribution (24h)",
        "oee_breakdown_24h": "OEE breakdown (24h)",
        "top_downtime_causes": "Top downtime causes (24h)",
        "predictions_summary": "Predictions summary",
        "data_quality_24h": "Data quality (24h)",
        "machine_inspector_title": "Machine inspector",
        "key_telemetry_live": "Key telemetry (live)",
        "latest_anomaly": "Latest anomaly",
        "health_score_label": "Health score",
        "failure_probability_label": "Failure probability",
        "rul_estimate_label": "RUL estimate",
        "temp_label": "Temp",
        "line_label": "Line",
        "station_label": "Station",
        "demo_data_note": "DEMO data",
        "data_lineage": "Data lineage",
        "last_record": "Last record",
        "sensor_rows_label": "Sensor rows",
        "production_rows_label": "Production rows",
        "model_rows_label": "Model rows",
        "source_label": "Source",
        "signal_drivers": "Signal drivers",
        "baseline_delta": "vs baseline",
        "calculation_basis": "Calculation basis",
        "calculation_basis_body": "Condition score is derived from vibration, wear, temperature, motor current, and torque in the selected machine stream.",
        "event_trail_ready": "Event trail ready",
        "maintenance_handoff": "Maintenance handoff",
        "writeback_not_connected": "CMMS/MES handoff sends only when a connector endpoint is configured for this DEMO data environment.",
        "workflow_subtitle": "Case lifecycle built from stored alerts, predictions, quality records, and sensor-derived signals.",
        "enterprise_controls": "Enterprise controls",
        "role_backed_users": "Role-backed users",
        "pending_approvals": "Pending approvals",
        "notification_queue": "Notification queue",
        "integration_outbox": "Integration outbox",
        "approval_policy": "Approval policy",
        "approval_policy_body": "High-severity resolution now requires supervisor approval. CMMS/MES handoffs are recorded in an outbox with audit events and notifications.",
        "dispatch_queue": "Connector handoff queue",
        "owners_label": "Case ownership",
        "queued_status": "Queued",
        "enterprise_actions": "Enterprise actions",
        "assign_owner": "Assign owner",
        "assignment_saved": "Owner assignment saved.",
        "request_approval": "Request approval",
        "approval_requested": "Approval requested.",
        "decide_approval": "Decide approval",
        "approval_decided": "Approval decision saved.",
        "dispatch_external": "Queue external handoff",
        "dispatch_queued": "External handoff queued.",
        "approval_type": "Approval type",
        "decision": "Decision",
        "target_system": "Target system",
        "reason": "Reason",
        "decision_note": "Decision note",
        "connector_health": "Connector health",
        "cmms_connector": "CMMS connector",
        "mes_connector": "MES connector",
        "sent_status": "Sent",
        "retrying_status": "Retrying",
        "failed_status": "Failed",
        "dead_letter_status": "Dead letter",
        "not_configured_status": "Not configured",
        "sync_workflow": "Sync workflow from live signals",
        "workflow_synced": "Workflow synced: {created} new, {updated} updated, {open_cases} open.",
        "open_cases": "Open cases",
        "critical_high_cases": "Critical / high",
        "unassigned_cases": "Unassigned",
        "due_cases": "Due now",
        "workflow_board": "Workflow board",
        "case_details": "Case details",
        "case_id": "รหัสเคส",
        "case_title": "เคส",
        "status": "Status",
        "severity": "Severity",
        "owner": "Owner",
        "source_type": "Source",
        "due_at": "Due",
        "last_seen_at": "Last seen",
        "next_action": "Next action",
        "evidence": "Evidence",
        "event_log": "Event log",
        "select_case": "Select case",
        "operator_note": "Operator note",
        "update_case": "Update case",
        "case_updated": "Case updated.",
        "no_workflow_cases": "No workflow cases yet. Sync workflow after data has arrived.",
        "new_status": "New",
        "triage_status": "Triage",
        "assigned_status": "Assigned",
        "investigating_status": "Investigating",
        "mitigated_status": "Mitigated",
        "resolved_status": "Resolved",
        "workflow_boundary": "This is a local DEMO data workflow store. CMMS/MES handoffs are sent only to configured connector endpoints; otherwise they remain visible in the governed outbox.",
        "trust_layer": "Trust layer",
        "metric_trust": "Metric trust",
        "action_queue_title": "Shift action queue",
        "action_queue_caption": "Prioritized from model output when available; otherwise from transparent sensor-derived and data-quality signals.",
        "risk_map_title": "Risk map",
        "drilldown_hint": "Open Machine investigation, Anomaly investigation, or Data quality for detailed records and operator actions.",
        "model_readiness": "Model readiness",
        "data_quality_gate": "Data quality gate",
        "open_action_count": "Open actions",
        "chart_time_window": "Time window",
        "select_station": "Select station",
        "all_stations": "All stations",
        "chart_points_caption": "Charts are filtered to the selected window and downsampled for readability.",
        "upper_threshold": "Upper threshold",
        "lower_threshold": "Lower threshold",
        "chart_focus": "Chart focus",
        "priority_stations": "Priority stations",
        "all_stations_in_chart": "All stations in chart",
        "chart_focus_caption": "Priority focus keeps charts legible by showing the highest-risk stations first.",
        "decision": "Decision",
        "eta": "ETA",
        "eta_now": "Now",
        "eta_this_shift": "This shift",
        "eta_today": "Today",
        "eta_next_check": "Next check",
        "owner_maintenance": "Maintenance",
        "owner_process_engineering": "Process engineering",
        "owner_data_engineering": "Data engineering",
        "owner_shift_lead": "Shift lead",
        "decision_machine": "Inspect machine trend",
        "decision_anomaly": "Confirm anomaly and production context",
        "decision_quality": "Verify data channel before escalation",
        "decision_monitor": "Monitor next ingest cycle",
        "driver": "Driver",
        "risk_units": "risk",
        "route": "Route",
        "route_machine": "Machine investigation",
        "route_anomaly": "Anomaly investigation",
        "route_quality": "Data quality",
        "route_workflow": "Workflow board",
    }
)

TEXT["th"].update(
    {
        "app_title": "ศูนย์ควบคุมข้อมูลการผลิต",
        "hero_label": "ระบบวิเคราะห์การผลิตแบบสด",
        "disclaimer": "ระบบ ingestion, API, SQLite และ dashboard ทำงานจริงบน DEMO data ทุกค่ามาจาก record ที่ collector/API บันทึกไว้และ analytics ที่คำนวณต่อจากข้อมูลนั้น",
        "site_name": "ศูนย์ปฏิบัติการ SMOP",
        "mode_name": "ข้อมูล DEMO ผ่านการรับข้อมูลสด",
        "database_caption": "ฐานข้อมูลรับข้อมูลในเครื่องที่หน้าควบคุมนี้ใช้งาน",
        "page_executive": "ศูนย์ควบคุม",
        "page_workflow": "ระบบติดตามงานปฏิบัติการ",
        "page_equipment": "ตรวจเครื่องจักรเชิงลึก",
        "page_anomaly": "ตรวจสัญญาณผิดปกติ",
        "page1_header": "1. ศูนย์ควบคุม",
        "page_workflow_header": "ระบบ workflow งานปฏิบัติการ",
        "page4_header": "4. ตรวจเครื่องจักรเชิงลึก",
        "page5_header": "5. ตรวจสัญญาณผิดปกติ",
        "section_note": "เริ่มจากภาพรวมของไลน์ แล้วเปิดการตรวจเครื่องเมื่อมีสัญญาณที่ต้องอ่านลึกขึ้น",
        "report_title": "รายงานศูนย์ควบคุมข้อมูลการผลิต",
        "rhythm_5": "ใช้หน้าจอนี้เป็นข้อมูล intelligence จาก record ที่เชื่อมเข้าระบบ และยืนยันการตัดสินใจตามขั้นตอนหน้างานก่อนใช้กับการผลิต",
        "limitations": "ขอบเขตการใช้งาน",
        "limitations_text": "หน้าจอนี้อ่านข้อมูลจาก SQLite, collector, API, model registry และ data quality records ที่มีอยู่ การใช้งานระดับโรงงานจริงยังต้องมี OT/IT integration ที่อนุมัติแล้ว, security review, historian หรือ PLC integration, maintenance label ที่ยืนยันได้, การตรวจจากเจ้าของกระบวนการ และ factory acceptance testing",
        "data_origin_title": "แหล่งที่มาของข้อมูล",
        "data_origin_body": "ทุกค่าบนหน้านี้อ่านจากฐานข้อมูล ingestion, model registry หรือคำนวณจาก DEMO data records ล่าสุด ไม่มีค่าที่ hardcode เพื่อหลอกหน้าจอ",
        "data_origin_scope": "แหล่ง input: DEMO data ที่ collector/API เขียนลง SQLite การใช้งานระดับ production ต้องเชื่อมเครื่องจริงและผ่านการยืนยันจากเจ้าของกระบวนการ",
        "plant_pulse": "ชีพจรของไลน์ผลิต",
        "machine_health_map": "แผนที่สุขภาพเครื่องจักร",
        "machine_health_map_caption": "คำนวณจาก record ล่าสุดของเครื่อง และใช้ health จากโมเดลเมื่อมี",
        "machine_matrix_empty": "ยังไม่มี record ของเครื่องจักร",
        "investigation_panel": "แผงตรวจเครื่องจักร",
        "investigation_panel_caption": "เลือกเครื่องเพื่อดู record สด คะแนนสภาพเครื่อง สัญญาณหลัก และ event trail ล่าสุด",
        "select_machine_for_deep_dive": "เลือกเครื่องจักรเพื่อดูเชิงลึก",
        "condition_score": "คะแนนสภาพเครื่อง",
        "derived_anomaly_index": "ดัชนีความผิดปกติที่คำนวณได้",
        "dominant_signal": "สัญญาณที่เด่นที่สุด",
        "latest_event": "เหตุการณ์ล่าสุด",
        "operating_context": "บริบทการเดินเครื่อง",
        "line_station": "ไลน์ / สถานี",
        "source_records": "จำนวน record ต้นทาง",
        "sensor_record_count": "sensor {value} แถว",
        "production_record_count": "production {value} แถว",
        "investigation_note": "นี่คือหน้าตรวจเชิงวิศวกรรม: ยืนยัน pattern ของสัญญาณ เทียบกับบริบทการผลิต แล้วตัดสินใจว่าจะเรียก model inference หรือให้ทีมซ่อมบำรุงตรวจต่อ",
        "machine_signal_trend": "แนวโน้มสัญญาณของเครื่อง",
        "machine_signal_trend_caption": "ค่า sensor ล่าสุดของเครื่องที่เลือก",
        "anomaly_timeline_derived": "ไทม์ไลน์การเบี่ยงเบนของสภาพเครื่อง",
        "anomaly_timeline_caption": "ถ้ายังไม่มี alert จากโมเดล ระบบจะคำนวณดัชนีผิดปกติแบบโปร่งใสจาก vibration, wear, current, torque และ temperature",
        "risk_normal": "ปกติ",
        "risk_low": "ต่ำ",
        "risk_elevated": "เริ่มสูง",
        "risk_high": "สูง",
        "risk_critical": "วิกฤต",
        "signal_vibration": "แรงสั่น",
        "signal_tool_wear": "การสึกของเครื่องมือ",
        "signal_temperature": "อุณหภูมิกระบวนการ",
        "signal_motor_current": "กระแสมอเตอร์",
        "signal_torque": "แรงบิด",
        "signal_balanced": "สัญญาณสมดุล",
        "no_machine_stream": "ยังไม่มี stream ของเครื่องที่เลือก",
        "detail_tab_overview": "ภาพรวม",
        "detail_tab_signals": "สัญญาณ",
        "detail_tab_events": "event trail",
        "detail_tab_context": "บริบท",
        "latest_sensor_record": "sensor record ล่าสุด",
        "latest_production_record": "production record ล่าสุด",
        "recent_machine_records": "record ล่าสุดของเครื่อง",
        "showing_database_records": "แสดง record สดจาก SQLite ในฐานข้อมูลที่ใช้งานอยู่",
        "model_status_body": "model registry ยังว่าง ระบบจึงแสดง condition analytics จาก sensor และ production record โดยตรง",
        "derived_anomaly_watchlist": "รายการสัญญาณผิดปกติที่คำนวณได้",
        "derived_anomaly_watchlist_caption": "จัดอันดับจาก sensor records เมื่อยังไม่มี alert จากโมเดล",
        "no_derived_anomaly_records": "ยังไม่มีสัญญาณผิดปกติที่คำนวณได้จาก stream ปัจจุบัน",
        "model_alerts_unavailable": "ตอนนี้ยังไม่มี alert จากโมเดล หน้านี้จึงใช้ดัชนีผิดปกติที่คำนวณจาก sensor records แบบโปร่งใส",
        "derived_diagnostic_hint": "บันทึก triage จาก sensor",
        "derived_recommended_action": "ตรวจแนวโน้มของเครื่องที่เลือก เทียบกับบริบทการผลิต และยืนยันว่าต้องส่งต่อซ่อมบำรุงหรือเรียกโมเดลหรือไม่",
        "command_center_title": "ศูนย์ควบคุมการผลิต",
        "live_label": "สด",
        "last_update": "อัปเดตล่าสุด",
        "shift_label": "กะเอ",
        "plant_label": "โรงงาน 1",
        "overview_nav_caption": "ศูนย์ควบคุม",
        "data_source_title": "แหล่งข้อมูล",
        "all_systems_operational": "ระบบทำงานปกติ",
        "ingestion_api": "API รับข้อมูล",
        "database_service": "ฐานข้อมูล",
        "collector_agents": "ตัวเก็บข้อมูล",
        "model_service": "บริการโมเดล",
        "view_data_pipeline": "ดูท่อข้อมูล",
        "model_run_count": "{value} รอบ",
        "record_count": "{value} รายการ",
        "overall_equipment_effectiveness": "ประสิทธิผลเครื่องจักรรวม",
        "active_lines": "ไลน์ที่ทำงาน",
        "machines_label": "เครื่องจักร",
        "anomalies_24h": "สัญญาณผิดปกติ 24 ชม.",
        "mttr_24h": "MTTR (24h)",
        "next_maintenance": "งานซ่อมถัดไป",
        "due_within_72": "ภายใน 72 ชั่วโมง",
        "running_label": "กำลังทำงาน",
        "critical_label": "วิกฤต",
        "warning_label": "เตือน",
        "line_risk_overview": "ภาพรวมความเสี่ยงของไลน์",
        "risk_score_weighted": "คะแนนความเสี่ยงถ่วงน้ำหนัก",
        "alerts_live": "สัญญาณเตือนสด",
        "view_all_alerts": "ดูสัญญาณเตือนทั้งหมด",
        "event_distribution_24h": "การกระจายเหตุการณ์ 24 ชม.",
        "oee_breakdown_24h": "องค์ประกอบ OEE 24 ชม.",
        "top_downtime_causes": "สาเหตุ downtime สูงสุด 24 ชม.",
        "predictions_summary": "สรุปผลคาดการณ์",
        "data_quality_24h": "คุณภาพข้อมูล 24 ชม.",
        "machine_inspector_title": "แผงตรวจเครื่องจักร",
        "key_telemetry_live": "สัญญาณสำคัญสด",
        "latest_anomaly": "สัญญาณผิดปกติล่าสุด",
        "health_score_label": "คะแนนสุขภาพ",
        "failure_probability_label": "โอกาสขัดข้อง",
        "rul_estimate_label": "เวลาใช้งานคงเหลือ",
        "temp_label": "อุณหภูมิ",
        "line_label": "ไลน์",
        "station_label": "สถานี",
        "demo_data_note": "ข้อมูล DEMO",
        "data_lineage": "ที่มาของข้อมูล",
        "last_record": "record ล่าสุด",
        "sensor_rows_label": "แถว sensor",
        "production_rows_label": "แถว production",
        "model_rows_label": "แถว model",
        "source_label": "แหล่งคำนวณ",
        "signal_drivers": "ตัวขับของสัญญาณ",
        "baseline_delta": "เทียบ baseline",
        "calculation_basis": "หลักการคำนวณ",
        "calculation_basis_body": "condition score คำนวณจาก vibration, wear, temperature, motor current และ torque ของ stream เครื่องที่เลือก",
        "event_trail_ready": "event trail พร้อมอ่าน",
        "maintenance_handoff": "ส่งต่อซ่อมบำรุง",
        "writeback_not_connected": "การส่งต่อ CMMS/MES จะยิงออกเมื่อมี endpoint ของ connector ตั้งค่าไว้ใน DEMO data environment นี้",
        "workflow_subtitle": "case lifecycle ที่สร้างจาก alerts, predictions, quality records และ sensor-derived signals ที่บันทึกไว้จริง",
        "enterprise_controls": "ส่วนควบคุมระดับ enterprise",
        "role_backed_users": "ผู้ใช้ที่มี role จริง",
        "pending_approvals": "approval ที่รอตัดสินใจ",
        "notification_queue": "คิวแจ้งเตือน",
        "integration_outbox": "integration outbox",
        "approval_policy": "นโยบาย approval",
        "approval_policy_body": "การปิด case ที่มีความรุนแรงสูงต้องผ่าน supervisor approval และการส่งต่อ CMMS/MES ถูกบันทึกใน outbox พร้อม audit event และ notification",
        "dispatch_queue": "คิวส่งต่อ connector",
        "owners_label": "เจ้าของ case",
        "queued_status": "เข้าคิวแล้ว",
        "enterprise_actions": "คำสั่งปฏิบัติการระดับ enterprise",
        "assign_owner": "มอบหมาย owner",
        "assignment_saved": "บันทึก owner แล้ว",
        "request_approval": "ขอ approval",
        "approval_requested": "ส่งคำขอ approval แล้ว",
        "decide_approval": "ตัดสินใจ approval",
        "approval_decided": "บันทึกผล approval แล้ว",
        "dispatch_external": "ส่งต่อระบบภายนอก",
        "dispatch_queued": "บันทึกคิวส่งต่อภายนอกแล้ว",
        "approval_type": "ประเภท approval",
        "decision": "ผลตัดสิน",
        "target_system": "ระบบปลายทาง",
        "reason": "เหตุผล",
        "decision_note": "บันทึกการตัดสินใจ",
        "connector_health": "สถานะ connector",
        "cmms_connector": "CMMS connector",
        "mes_connector": "MES connector",
        "sent_status": "ส่งแล้ว",
        "retrying_status": "กำลัง retry",
        "failed_status": "ล้มเหลว",
        "dead_letter_status": "dead letter",
        "not_configured_status": "ยังไม่ตั้งค่า",
        "sync_workflow": "ซิงก์ workflow จากสัญญาณล่าสุด",
        "workflow_synced": "ซิงก์แล้ว: สร้างใหม่ {created}, อัปเดต {updated}, เปิดอยู่ {open_cases}",
        "open_cases": "เคสที่เปิดอยู่",
        "critical_high_cases": "วิกฤต / สูง",
        "unassigned_cases": "ยังไม่มีผู้รับผิดชอบ",
        "due_cases": "ถึงกำหนดแล้ว",
        "workflow_board": "บอร์ดงาน",
        "case_details": "รายละเอียดเคส",
        "case_id": "รหัสเคส",
        "case_title": "เคส",
        "status": "สถานะ",
        "severity": "ความรุนแรง",
        "owner": "ผู้รับผิดชอบ",
        "source_type": "แหล่งสัญญาณ",
        "due_at": "กำหนด",
        "last_seen_at": "เห็นล่าสุด",
        "next_action": "งานถัดไป",
        "evidence": "หลักฐาน",
        "event_log": "event log",
        "select_case": "เลือก case",
        "operator_note": "บันทึก operator",
        "update_case": "อัปเดต case",
        "case_updated": "อัปเดต case แล้ว",
        "no_workflow_cases": "ยังไม่มี workflow case ให้ซิงก์หลังมีข้อมูลเข้าระบบ",
        "new_status": "ใหม่",
        "triage_status": "คัดกรอง",
        "assigned_status": "มอบหมายแล้ว",
        "investigating_status": "กำลังตรวจ",
        "mitigated_status": "ลดผลกระทบแล้ว",
        "resolved_status": "ปิดแล้ว",
        "workflow_boundary": "นี่คือ local DEMO data workflow store การส่งต่อ CMMS/MES จะยิงไป endpoint ที่ตั้งค่าไว้เท่านั้น ถ้ายังไม่ตั้งค่าระบบจะเก็บไว้ใน governed outbox ให้ตรวจสอบได้",
        "trust_layer": "ชั้นความน่าเชื่อถือ",
        "metric_trust": "ระดับความน่าเชื่อถือของตัวเลข",
        "action_queue_title": "คิวงานประจำกะ",
        "action_queue_caption": "จัดลำดับจากผลโมเดลเมื่อมีข้อมูล ถ้ายังไม่มีโมเดลจะใช้สัญญาณที่คำนวณจาก sensor และ data quality แบบโปร่งใส",
        "risk_map_title": "แผนที่ความเสี่ยง",
        "drilldown_hint": "เปิดหน้าตรวจเครื่องจักร ตรวจสัญญาณผิดปกติ หรือคุณภาพข้อมูล เพื่อดู record และ action แบบละเอียด",
        "model_readiness": "ความพร้อมของโมเดล",
        "data_quality_gate": "ประตูตรวจคุณภาพข้อมูล",
        "open_action_count": "งานที่ต้องติดตาม",
        "chart_time_window": "ช่วงเวลา",
        "select_station": "เลือกสถานี",
        "all_stations": "ทุกสถานี",
        "chart_points_caption": "กราฟถูกกรองตามช่วงเวลาที่เลือกและลดจำนวนจุดเพื่อให้อ่านง่าย",
        "upper_threshold": "ขีดจำกัดบน",
        "lower_threshold": "ขีดจำกัดล่าง",
        "chart_focus": "โฟกัสกราฟ",
        "priority_stations": "สถานีเสี่ยงสูงสุด",
        "all_stations_in_chart": "ทุกสถานีในกราฟ",
        "chart_focus_caption": "โฟกัสสถานีเสี่ยงช่วยให้กราฟอ่านง่าย โดยแสดงจุดที่ควรดูมากที่สุดก่อน",
        "decision": "การตัดสินใจ",
        "eta": "เวลาตอบสนอง",
        "eta_now": "ทันที",
        "eta_this_shift": "ภายในกะนี้",
        "eta_today": "วันนี้",
        "eta_next_check": "รอบตรวจถัดไป",
        "owner_maintenance": "ทีมซ่อมบำรุง",
        "owner_process_engineering": "วิศวกรกระบวนการ",
        "owner_data_engineering": "วิศวกรข้อมูล",
        "owner_shift_lead": "หัวหน้ากะ",
        "decision_machine": "ตรวจแนวโน้มเครื่องจักร",
        "decision_anomaly": "ยืนยันสัญญาณผิดปกติกับบริบทการผลิต",
        "decision_quality": "ตรวจช่องทางข้อมูลก่อนยกระดับ",
        "decision_monitor": "ติดตามรอบรับข้อมูลถัดไป",
        "driver": "สาเหตุหลัก",
        "risk_units": "ความเสี่ยง",
        "route": "เปิดดู",
        "route_machine": "ตรวจเครื่องจักร",
        "route_anomaly": "ตรวจสัญญาณผิดปกติ",
        "route_quality": "คุณภาพข้อมูล",
        "route_workflow": "บอร์ด workflow",
    }
)

TEXT["zh"].update({key: value for key, value in TEXT["en"].items() if key not in TEXT["zh"]})
TEXT["ja"].update({key: value for key, value in TEXT["en"].items() if key not in TEXT["ja"]})

TEXT["zh"].update(
    {
        "app_title": "制造数据运营控制台",
        "hero_label": "实时制造智能",
        "disclaimer": "真实 ingestion、API、SQLite 和 dashboard 流程正在使用 DEMO data。所有数值来自已存储的 collector/API 记录和派生分析。",
        "site_name": "SMOP 运营单元",
        "mode_name": "DEMO data 实时接入",
        "database_caption": "运营控制台使用的本地接入数据库。",
        "page_executive": "控制中心",
        "page_equipment": "设备深度调查",
        "page_anomaly": "异常深度调查",
        "page1_header": "1. 控制中心",
        "page4_header": "4. 设备深度调查",
        "page5_header": "5. 异常深度调查",
        "section_note": "先查看产线整体状态；当信号需要深读时，再打开设备调查。",
        "report_title": "制造数据运营报告",
        "rhythm_5": "将控制台作为来自已接入记录的运营情报；生产决策前仍需按现场流程确认。",
        "limitations": "部署边界",
        "limitations_text": "本控制台读取可用的 SQLite、collector、API、模型和数据质量记录。工厂级使用仍需要获批的 OT/IT 集成、安全审查、historian 或 PLC 集成、已验证维护标签、流程负责人审核和工厂验收测试。",
        "data_origin_title": "数据来源",
        "data_origin_body": "屏幕上的每个值都来自本地接入数据库、模型注册表，或由近期 DEMO data 记录计算得出。没有硬编码指标。",
        "data_origin_scope": "输入来源：collector/API 写入 SQLite 的 DEMO data。生产使用需要真实设备接入和负责人签核。",
        "plant_pulse": "产线脉搏",
        "machine_health_map": "设备健康地图",
        "machine_health_map_caption": "基于最新设备记录；有模型健康分时优先使用模型结果。",
        "machine_matrix_empty": "还没有设备记录。",
        "investigation_panel": "设备调查面板",
        "investigation_panel_caption": "选择设备查看实时记录、状态分、主要信号和近期事件轨迹。",
        "select_machine_for_deep_dive": "选择设备进行深度查看",
        "condition_score": "状态分",
        "derived_anomaly_index": "推导异常指数",
        "dominant_signal": "主要信号",
        "latest_event": "最新事件",
        "operating_context": "运行上下文",
        "line_station": "产线 / 工位",
        "source_records": "来源记录数",
        "sensor_record_count": "{value} 条传感器记录",
        "production_record_count": "{value} 条生产记录",
        "investigation_note": "这是工程 triage 视图：确认信号模式，对照生产上下文，再决定是否需要模型推理或维护复核。",
        "machine_signal_trend": "设备信号趋势",
        "machine_signal_trend_caption": "所选设备的近期传感器值。",
        "anomaly_timeline_derived": "状态漂移时间线",
        "anomaly_timeline_caption": "模型告警不可用时，控制台会从振动、磨损、电流、扭矩和温度记录推导透明异常指数。",
        "risk_normal": "稳定",
        "risk_elevated": "升高",
        "risk_high": "高",
        "risk_critical": "严重",
        "signal_vibration": "振动",
        "signal_tool_wear": "刀具磨损",
        "signal_temperature": "过程温度",
        "signal_motor_current": "电机电流",
        "signal_torque": "扭矩",
        "signal_balanced": "信号均衡",
        "no_machine_stream": "所选设备还没有数据流。",
        "detail_tab_overview": "概览",
        "detail_tab_signals": "信号",
        "detail_tab_events": "事件轨迹",
        "detail_tab_context": "上下文",
        "latest_sensor_record": "最新传感器记录",
        "latest_production_record": "最新生产记录",
        "recent_machine_records": "近期设备记录",
        "showing_database_records": "显示来自当前数据库的 SQLite 实时记录。",
        "model_status_body": "模型注册表为空。控制台仍会直接从传感器和生产记录显示状态分析。",
        "derived_anomaly_watchlist": "推导异常关注列表",
        "derived_anomaly_watchlist_caption": "模型告警不可用时，按传感器记录排序生成。",
        "no_derived_anomaly_records": "当前传感器流还没有可推导的异常记录。",
        "model_alerts_unavailable": "模型告警尚不可用，因此本视图使用透明的传感器推导异常指数。",
        "derived_diagnostic_hint": "传感器推导 triage 说明",
        "derived_recommended_action": "复查所选设备趋势，对照生产上下文，确认是否需要维护或模型推理。",
        "data_lineage": "数据血缘",
        "last_record": "最新记录",
        "sensor_rows_label": "传感器记录",
        "production_rows_label": "生产记录",
        "model_rows_label": "模型记录",
        "source_label": "来源",
        "signal_drivers": "信号驱动因素",
        "baseline_delta": "相对基线",
        "calculation_basis": "计算依据",
        "calculation_basis_body": "状态分由所选设备流中的振动、磨损、温度、电机电流和扭矩计算得出。",
        "event_trail_ready": "事件轨迹可查看",
        "maintenance_handoff": "维护交接",
        "writeback_not_connected": "此 DEMO data 环境未连接工单写回系统。",
    }
)

TEXT["ja"].update(
    {
        "app_title": "製造データ運用コンソール",
        "hero_label": "リアルタイム製造インテリジェンス",
        "disclaimer": "実際の ingestion、API、SQLite、dashboard ワークフローが DEMO data 上で動作しています。値は保存済み collector/API レコードと派生分析から来ています。",
        "site_name": "SMOP オペレーションセル",
        "mode_name": "DEMO data ライブ取り込み",
        "database_caption": "運用コンソールが使用するローカル取り込みデータベース。",
        "page_executive": "コマンドセンター",
        "page_equipment": "設備深掘り調査",
        "page_anomaly": "異常深掘り調査",
        "page1_header": "1. コマンドセンター",
        "page4_header": "4. 設備深掘り調査",
        "page5_header": "5. 異常深掘り調査",
        "section_note": "まずライン全体を確認し、注意すべき信号があれば設備調査を開いて深く読みます。",
        "report_title": "製造データ運用レポート",
        "rhythm_5": "接続済みレコードからの運用インテリジェンスとして利用し、生産判断の前に現場手順で確認します。",
        "limitations": "導入範囲",
        "limitations_text": "このコンソールは利用可能な SQLite、collector、API、モデル、データ品質レコードを読み取ります。工場レベルで使うには、承認済み OT/IT 連携、セキュリティレビュー、historian または PLC 連携、検証済み保全ラベル、工程責任者レビュー、工場受入試験が必要です。",
        "data_origin_title": "データの出所",
        "data_origin_body": "画面上の値はすべてローカル取り込みデータベース、モデルレジストリ、または直近の DEMO data レコードからの計算値です。ハードコードされた値はありません。",
        "data_origin_scope": "入力元: collector/API が SQLite に書き込んだ DEMO data。production 利用には実機連携と責任者承認が必要です。",
        "plant_pulse": "ラインの脈動",
        "machine_health_map": "設備状態マップ",
        "machine_health_map_caption": "最新設備レコードから計算し、モデルの健康スコアがあればそれを使用します。",
        "machine_matrix_empty": "設備レコードはまだありません。",
        "investigation_panel": "設備調査パネル",
        "investigation_panel_caption": "設備を選ぶと、ライブレコード、状態スコア、主要信号、直近イベント履歴を確認できます。",
        "select_machine_for_deep_dive": "深掘りする設備を選択",
        "condition_score": "状態スコア",
        "derived_anomaly_index": "算出異常指数",
        "dominant_signal": "主なシグナル",
        "latest_event": "最新イベント",
        "operating_context": "稼働コンテキスト",
        "line_station": "ライン / ステーション",
        "source_records": "元レコード数",
        "sensor_record_count": "センサーレコード {value} 件",
        "production_record_count": "生産レコード {value} 件",
        "investigation_note": "これはエンジニアリング triage 画面です。信号パターンを確認し、生産コンテキストと照合して、モデル推論または保全確認が必要か判断します。",
        "machine_signal_trend": "設備シグナル推移",
        "machine_signal_trend_caption": "選択設備の直近センサー値。",
        "anomaly_timeline_derived": "状態ドリフトタイムライン",
        "anomaly_timeline_caption": "モデルアラートがない場合、振動、摩耗、電流、トルク、温度レコードから透明な異常指数を算出します。",
        "risk_normal": "安定",
        "risk_elevated": "上昇",
        "risk_high": "高",
        "risk_critical": "重大",
        "signal_vibration": "振動",
        "signal_tool_wear": "工具摩耗",
        "signal_temperature": "プロセス温度",
        "signal_motor_current": "モーター電流",
        "data_lineage": "データリネージ",
        "last_record": "最新レコード",
        "sensor_rows_label": "センサーレコード",
        "production_rows_label": "生産レコード",
        "model_rows_label": "モデルレコード",
        "source_label": "ソース",
        "signal_drivers": "シグナルドライバー",
        "baseline_delta": "ベースライン比",
        "calculation_basis": "計算根拠",
        "calculation_basis_body": "状態スコアは、選択設備の振動、摩耗、温度、モーター電流、トルクから算出します。",
        "event_trail_ready": "イベント履歴を確認可能",
        "maintenance_handoff": "保全引き継ぎ",
        "writeback_not_connected": "この DEMO data 環境では作業指示の書き戻しは未接続です。",
        "signal_torque": "トルク",
        "signal_balanced": "バランスした信号",
        "no_machine_stream": "選択した設備のストリームはまだありません。",
        "detail_tab_overview": "概要",
        "detail_tab_signals": "信号",
        "detail_tab_events": "イベント履歴",
        "detail_tab_context": "コンテキスト",
        "latest_sensor_record": "最新センサーレコード",
        "latest_production_record": "最新生産レコード",
        "recent_machine_records": "直近設備レコード",
        "showing_database_records": "稼働中のデータベースから SQLite のライブレコードを表示しています。",
        "model_status_body": "モデルレジストリは空です。コンソールはセンサーと生産レコードから状態分析を表示します。",
        "derived_anomaly_watchlist": "算出異常ウォッチリスト",
        "derived_anomaly_watchlist_caption": "モデルアラートがない場合、センサーレコードから順位付けします。",
        "no_derived_anomaly_records": "現在のセンサーストリームから算出できる異常レコードはありません。",
        "model_alerts_unavailable": "モデルアラートがまだないため、この画面では透明なセンサー由来の異常指数を使います。",
        "derived_diagnostic_hint": "センサー由来 triage メモ",
        "derived_recommended_action": "選択設備のトレンドを確認し、生産コンテキストと比較して、保全またはモデル推論が必要か判断します。",
    }
)

COLUMN_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "priority": "Priority",
        "area": "Area",
        "asset": "Asset",
        "signal": "Signal",
        "suggested_action": "Suggested action",
        "timestamp": "Time",
        "created_at": "Created at",
        "detected_at": "Detected at",
        "machine_id": "Machine",
        "line_id": "Line",
        "station_id": "Station",
        "cycle_time_sec": "Cycle time sec",
        "station_yield": "Station yield",
        "throughput_count": "Throughput",
        "target_throughput": "Target throughput",
        "reject_count": "Reject count",
        "defect_rate": "Defect rate",
        "micro_stop_count": "Micro stops",
        "downtime_minutes": "Downtime minutes",
        "vibration_rms": "Vibration RMS",
        "process_temperature": "Process temperature",
        "motor_current": "Motor current",
        "torque": "Torque",
        "tool_wear": "Tool wear",
        "risk_level": "Risk level",
        "health_score": "Health score",
        "failure_probability": "Failure probability",
        "rul_estimate_hours": "RUL hours",
        "anomaly_score": "Anomaly score",
        "severity": "Severity",
        "message": "Message",
        "source": "Source",
        "hint": "Note",
        "diagnostic_hint": "Diagnostic note",
        "recommended_action": "Recommended action",
        "issue_type": "Issue type",
        "entity_type": "Entity type",
        "details_json": "Details",
        "id": "ID",
        "model_name": "Model name",
        "model_type": "Model type",
        "model_version": "Version",
        "artifact_path": "Artifact path",
        "training_rows": "Training rows",
        "test_rows": "Test rows",
        "completed_at": "Completed at",
        "status": "Status",
        "feature": "Feature",
        "importance": "Importance",
        "count": "Count",
        "records": "Records",
        "type": "Type",
    },
}

COLUMN_LABELS["th"] = {
    **COLUMN_LABELS["en"],
    "priority": "ความสำคัญ",
    "area": "พื้นที่",
    "asset": "เครื่องหรือระบบ",
    "signal": "สัญญาณ",
    "suggested_action": "สิ่งที่ควรทำ",
    "timestamp": "เวลา",
    "created_at": "สร้างเมื่อ",
    "detected_at": "ตรวจพบเมื่อ",
    "machine_id": "เครื่องจักร",
    "line_id": "ไลน์",
    "station_id": "สถานี",
    "cycle_time_sec": "cycle time วินาที",
    "station_yield": "yield ของสถานี",
    "throughput_count": "ผลผลิต",
    "target_throughput": "เป้าหมายผลผลิต",
    "reject_count": "จำนวน reject",
    "defect_rate": "อัตรา defect",
    "micro_stop_count": "จำนวน micro stop",
    "downtime_minutes": "downtime นาที",
    "vibration_rms": "แรงสั่น RMS",
    "process_temperature": "อุณหภูมิกระบวนการ",
    "motor_current": "กระแสมอเตอร์",
    "torque": "แรงบิด",
    "tool_wear": "การสึกของเครื่องมือ",
    "risk_level": "ระดับความเสี่ยง",
    "health_score": "คะแนนสุขภาพ",
    "failure_probability": "โอกาสเสีย",
    "rul_estimate_hours": "RUL ชั่วโมง",
    "anomaly_score": "คะแนนความผิดปกติ",
    "severity": "ระดับความรุนแรง",
    "message": "ข้อความ",
    "source": "แหล่งที่มา",
    "hint": "บันทึก",
    "diagnostic_hint": "บันทึกช่วยวิเคราะห์",
    "recommended_action": "สิ่งที่แนะนำให้ทำ",
    "issue_type": "ประเภทปัญหา",
    "entity_type": "ประเภทข้อมูล",
    "details_json": "รายละเอียด",
    "model_name": "ชื่อโมเดล",
    "model_type": "ประเภทโมเดล",
    "model_version": "เวอร์ชัน",
    "artifact_path": "ตำแหน่ง artifact",
    "training_rows": "แถวฝึก",
    "test_rows": "แถวทดสอบ",
    "completed_at": "เสร็จเมื่อ",
    "status": "สถานะ",
    "feature": "feature",
    "importance": "ความสำคัญ",
    "count": "จำนวน",
    "records": "จำนวนข้อมูล",
    "type": "ประเภท",
}

COLUMN_LABELS["zh"] = {
    **COLUMN_LABELS["en"],
    "priority": "优先级",
    "area": "区域",
    "asset": "设备或系统",
    "signal": "信号",
    "suggested_action": "建议操作",
    "timestamp": "时间",
    "machine_id": "设备",
    "line_id": "产线",
    "station_id": "工位",
    "health_score": "健康分",
    "risk_level": "风险等级",
    "anomaly_score": "异常分数",
    "recommended_action": "建议操作",
    "issue_type": "问题类型",
    "severity": "严重级别",
    "count": "数量",
}

COLUMN_LABELS["ja"] = {
    **COLUMN_LABELS["en"],
    "priority": "優先度",
    "area": "エリア",
    "asset": "設備またはシステム",
    "signal": "シグナル",
    "suggested_action": "推奨アクション",
    "timestamp": "時刻",
    "machine_id": "設備",
    "line_id": "ライン",
    "station_id": "ステーション",
    "health_score": "健康スコア",
    "risk_level": "リスクレベル",
    "anomaly_score": "異常スコア",
    "recommended_action": "推奨アクション",
    "issue_type": "問題タイプ",
    "severity": "重大度",
    "count": "件数",
}

for _labels in COLUMN_LABELS.values():
    _labels.update(
        {
            "condition_score": "Condition score",
            "derived_anomaly_index": "Derived anomaly index",
            "dominant_signal": "Dominant signal",
            "source": "Source",
            "record_count": "Record count",
            "latest_value": "Latest value",
            "line_station": "Line / station",
            "operating_context": "Operating context",
            "station_yield": "Station yield",
            "cycle_time_sec": "Cycle time sec",
            "defect_rate": "Defect rate",
        }
    )

COLUMN_LABELS["th"].update(
    {
        "condition_score": "คะแนนสภาพเครื่อง",
        "derived_anomaly_index": "ดัชนีความผิดปกติ",
        "dominant_signal": "สัญญาณหลัก",
        "source": "แหล่งที่มา",
        "record_count": "จำนวน record",
        "latest_value": "ค่าล่าสุด",
        "line_station": "ไลน์ / สถานี",
        "operating_context": "บริบทการเดินเครื่อง",
    }
)

COLUMN_LABELS["zh"].update(
    {
        "condition_score": "状态分",
        "derived_anomaly_index": "异常指数",
        "dominant_signal": "主要信号",
        "source": "来源",
        "record_count": "记录数",
        "latest_value": "最新值",
        "line_station": "产线 / 工位",
        "operating_context": "运行上下文",
    }
)

COLUMN_LABELS["ja"].update(
    {
        "condition_score": "状態スコア",
        "derived_anomaly_index": "異常指数",
        "dominant_signal": "主なシグナル",
        "source": "ソース",
        "record_count": "記録数",
        "latest_value": "最新値",
        "line_station": "ライン / ステーション",
        "operating_context": "稼働コンテキスト",
    }
)


def t(lang: str, key: str, **kwargs: Any) -> str:
    """Return localized UI text with English fallback."""
    text = TEXT.get(lang, TEXT[DEFAULT_LANGUAGE]).get(key, TEXT[DEFAULT_LANGUAGE].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def language_index() -> int:
    """Return the selected language index for the sidebar control."""
    current = st.session_state.get("smop_language", DEFAULT_LANGUAGE)
    keys = list(LANGUAGE_OPTIONS)
    return keys.index(current) if current in keys else keys.index(DEFAULT_LANGUAGE)


def localize_columns(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    """Rename common dataframe columns for the selected language."""
    if df.empty:
        return df
    labels = COLUMN_LABELS.get(lang, COLUMN_LABELS[DEFAULT_LANGUAGE])
    fallback = COLUMN_LABELS[DEFAULT_LANGUAGE]
    renamed = {
        col: labels.get(col, fallback.get(col, str(col).replace("_", " ").title()))
        for col in df.columns
    }
    return df.rename(columns=renamed)


def display_dataframe(df: pd.DataFrame, lang: str, **kwargs: Any) -> None:
    """Render a dataframe with human-facing column names."""
    if "use_container_width" in kwargs:
        kwargs["width"] = "stretch" if kwargs.pop("use_container_width") else "content"
    st.dataframe(localize_columns(df, lang), **kwargs)


def inject_global_style() -> None:
    """Apply a production-style visual system to the Streamlit dashboard."""
    st.markdown(
        """
<style>
:root {
    --smop-bg: #07110d;
    --smop-bg-2: #0b1f17;
    --smop-panel: #f8fbf8;
    --smop-ink: #0b1410;
    --smop-muted: #6b7b73;
    --smop-border: #d9e6de;
    --smop-grid: rgba(121, 218, 88, .13);
    --smop-info: #00a3b5;
    --smop-ok: #36c95f;
    --smop-warn: #d5a026;
    --smop-risk: #e45353;
    --smop-green: #74d943;
    --smop-cyan: #37d7cc;
}
.stApp {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background:
        linear-gradient(90deg, rgba(103, 227, 74, .026) 1px, transparent 1px) 0 0 / 28px 28px,
        linear-gradient(180deg, rgba(54, 216, 208, .018) 1px, transparent 1px) 0 0 / 28px 28px,
        radial-gradient(circle at 78% 0%, rgba(54, 216, 208, .12), transparent 24rem),
        radial-gradient(circle at 18% 0%, rgba(103, 227, 74, .075), transparent 18rem),
        linear-gradient(145deg, #050706 0%, #07100d 52%, #040706 100%);
}
.block-container {
    padding-top: 1rem;
    padding-bottom: 2.5rem;
    max-width: 1280px;
}
[data-testid="stSidebar"] {
    min-width: 236px !important;
    max-width: 236px !important;
    background:
        linear-gradient(180deg, rgba(103, 227, 74, .08), transparent 15rem),
        linear-gradient(180deg, #080d0b 0%, #050807 100%);
    border-right: 1px solid rgba(255, 255, 255, .08);
}
[data-testid="stSidebar"] > div:first-child {
    width: 236px !important;
}
[data-testid="stSidebar"] * {
    color: #eaf4ed;
}
[data-testid="stSidebar"] .stButton button {
    width: 100%;
    border-radius: 999px;
    border: 1px solid rgba(116, 217, 67, .33);
    background: rgba(116, 217, 67, .09);
    color: #effff1;
    font-weight: 700;
}
.smop-hero {
    position: relative;
    overflow: hidden;
    padding: 1.25rem 1.45rem 1.35rem;
    border-radius: 10px;
    background:
        linear-gradient(90deg, rgba(116, 217, 67, .18), transparent 1px) 0 0 / 26px 26px,
        linear-gradient(180deg, rgba(55, 215, 204, .12), transparent 1px) 0 0 / 26px 26px,
        linear-gradient(135deg, rgba(9, 33, 24, .96) 0%, rgba(18, 56, 39, .94) 48%, rgba(11, 77, 70, .92) 100%);
    color: #f4fff5;
    border: 1px solid rgba(116, 217, 67, .26);
    box-shadow: 0 20px 70px rgba(0, 0, 0, .34);
    margin-bottom: .95rem;
}
.smop-hero h1 {
    margin: 0;
    font-size: 2.08rem;
    letter-spacing: 0;
    line-height: 1.08;
}
.smop-hero p {
    max-width: 56rem;
    margin: .55rem 0 0 0;
    color: rgba(237, 255, 241, .78);
}
.smop-command-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr);
    gap: 1rem;
    margin: .9rem 0 1.1rem;
}
.smop-card {
    background:
        linear-gradient(180deg, rgba(255,255,255,.98), rgba(244, 251, 246, .96));
    border: 1px solid rgba(217, 230, 222, .86);
    border-radius: 8px;
    padding: 1rem 1.05rem;
    box-shadow: 0 14px 38px rgba(0, 0, 0, .22);
    margin-bottom: .8rem;
}
.smop-card-title {
    color: #496358;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .04em;
    text-transform: uppercase;
    margin-bottom: .35rem;
}
.smop-card-value {
    color: var(--smop-ink);
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
    padding: .24rem .66rem;
    border-radius: 999px;
    font-size: .78rem;
    font-weight: 700;
    margin-right: .35rem;
    margin-bottom: .35rem;
}
.smop-pill-ok {
    color: #063d23;
    background: #c7f8d3;
    border: 1px solid #74d943;
}
.smop-pill-warn {
    color: #513805;
    background: #fff0b8;
    border: 1px solid #d5a026;
}
.smop-pill-risk {
    color: #5b1010;
    background: #ffd7d7;
    border: 1px solid #e45353;
}
.smop-pill-info {
    color: #06343c;
    background: #d6fffb;
    border: 1px solid #37d7cc;
}
.trust-badge-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: .28rem;
    margin-top: .45rem;
}
.trust-badge {
    display: inline-flex;
    align-items: center;
    min-height: 1.3rem;
    padding: .16rem .45rem;
    border-radius: 3px;
    font-size: .66rem;
    font-weight: 850;
    letter-spacing: .02em;
    text-transform: uppercase;
}
.trust-ok {
    color: #092012;
    background: #75e250;
}
.trust-info {
    color: #061c21;
    background: #4ce0d8;
}
.trust-warn {
    color: #241801;
    background: #f4ce31;
}
.trust-risk {
    color: #fff5f2;
    background: #ff5148;
}
.smop-section-note {
    padding: .85rem 1rem;
    border-left: 4px solid var(--smop-green);
    background: rgba(235, 255, 238, .94);
    border-radius: 8px;
    color: #143d26;
    margin: .5rem 0 1rem;
}
.smop-tiny {
    color: rgba(215, 255, 225, .64);
    font-size: .82rem;
    letter-spacing: .04em;
    text-transform: uppercase;
}
.smop-notice {
    background: linear-gradient(135deg, rgba(235,255,238,.98), rgba(225,255,250,.95));
    border: 1px solid rgba(116,217,67,.42);
    border-left: 5px solid var(--smop-green);
    border-radius: 8px;
    color: #123821;
    padding: .85rem 1rem;
    margin: .65rem 0 .95rem;
    box-shadow: 0 12px 32px rgba(0,0,0,.18);
}
.smop-notice-title {
    font-size: .84rem;
    font-weight: 800;
    letter-spacing: .04em;
    text-transform: uppercase;
    margin-bottom: .25rem;
}
.smop-inspector {
    background: linear-gradient(180deg, rgba(10, 25, 19, .96), rgba(7, 17, 13, .98));
    border: 1px solid rgba(116, 217, 67, .24);
    border-radius: 10px;
    padding: 1rem;
    color: #ecfff0;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.03), 0 18px 50px rgba(0,0,0,.25);
}
.smop-inspector .smop-card {
    box-shadow: none;
}
.smop-inspector-title {
    font-size: 1.2rem;
    font-weight: 800;
    margin-bottom: .2rem;
}
.smop-inspector-caption {
    color: rgba(236,255,240,.7);
    font-size: .88rem;
    margin-bottom: .9rem;
}
.smop-kv {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: .65rem;
}
.smop-kv-item {
    border: 1px solid rgba(116,217,67,.18);
    border-radius: 8px;
    padding: .68rem .75rem;
    background: rgba(255,255,255,.04);
}
.smop-kv-label {
    font-size: .72rem;
    color: rgba(236,255,240,.62);
    text-transform: uppercase;
    letter-spacing: .04em;
}
.smop-kv-value {
    margin-top: .18rem;
    font-weight: 760;
    color: #f7fff8;
    overflow-wrap: anywhere;
}
[data-testid="stMetricValue"] {
    color: #ebfff0;
    font-weight: 760;
    font-size: 1.72rem;
    line-height: 1.08;
}
[data-testid="stMetricLabel"] {
    color: rgba(220, 248, 226, .62);
    min-height: 2.1rem;
    display: flex;
    align-items: flex-end;
    line-height: 1.25;
}
[data-testid="stMetric"] {
    min-height: 6.7rem;
    padding: .82rem .88rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 5px;
    background: linear-gradient(180deg, rgba(21, 27, 27, .84), rgba(10, 14, 15, .72));
}
[data-testid="stMetric"] + [data-testid="stMarkdownContainer"] {
    margin-top: -.45rem;
}
.metric-trust-card {
    min-height: 6.3rem;
    padding: .78rem .82rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 5px;
    background: linear-gradient(180deg, rgba(21, 27, 27, .84), rgba(10, 14, 15, .72));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
}
.metric-trust-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: .65rem;
    min-height: 2.05rem;
}
.metric-trust-label {
    color: rgba(220, 248, 226, .64);
    font-size: .76rem;
    font-weight: 760;
    line-height: 1.24;
}
.metric-trust-value {
    color: #ebfff0;
    font-size: 1.7rem;
    font-weight: 800;
    line-height: 1.08;
    margin-top: .3rem;
    overflow-wrap: anywhere;
}
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label {
    min-height: 1.35rem;
    color: rgba(234,244,233,.72) !important;
    font-size: .74rem;
    font-weight: 760;
}
div[data-testid="stPlotlyChart"] {
    margin-top: .45rem;
    margin-bottom: 1rem;
    padding: .45rem .55rem .15rem;
    border: 1px solid rgba(255,255,255,.085);
    border-radius: 6px;
    background:
        radial-gradient(circle at 8% 0%, rgba(55, 215, 204, .045), transparent 16rem),
        linear-gradient(180deg, rgba(21, 27, 27, .74), rgba(8, 12, 13, .62));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.035), 0 16px 34px rgba(0,0,0,.20);
}
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(116,217,67,.18);
    border-radius: 8px;
    overflow: hidden;
}
@media (max-width: 900px) {
    .smop-command-grid {
        grid-template-columns: 1fr;
    }
    .smop-hero h1 {
        font-size: 1.65rem;
    }
}
header[data-testid="stHeader"] {
    display: none;
}
.block-container {
    max-width: 1560px;
    padding-top: .85rem;
    padding-left: 1.35rem;
    padding-right: 1.35rem;
}
[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 14% 0%, rgba(103, 232, 74, .12), transparent 16rem),
        linear-gradient(180deg, #08100d 0%, #070b0a 100%);
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    display: flex !important;
    align-items: center;
    border-radius: 4px;
    padding: .58rem .55rem;
    margin: .12rem 0;
    border-left: 3px solid transparent;
}
[data-testid="stSidebar"] [role="radiogroup"] label::before {
    content: "";
    display: inline-block;
    width: .86rem;
    height: .86rem;
    margin-right: .58rem;
    border-radius: 3px;
    border: 1px solid rgba(226, 242, 223, .42);
    background:
        linear-gradient(90deg, transparent 45%, rgba(226,242,223,.38) 45% 55%, transparent 55%),
        linear-gradient(180deg, transparent 45%, rgba(226,242,223,.38) 45% 55%, transparent 55%);
    opacity: .72;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(96, 196, 64, .25);
    border-left-color: #69e044;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before {
    border-color: #75ef52;
    background:
        linear-gradient(90deg, transparent 45%, rgba(5,12,6,.7) 45% 55%, transparent 55%),
        linear-gradient(180deg, transparent 45%, rgba(5,12,6,.7) 45% 55%, transparent 55%),
        #69e044;
    opacity: 1;
}
[data-testid="stSidebar"] input[type="radio"] {
    accent-color: #69e044;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child,
[data-testid="stSidebar"] label[data-baseweb="radio"] input[type="radio"],
[data-testid="stSidebar"] [role="radiogroup"] svg {
    display: none !important;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] p {
    margin: 0;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] code {
    white-space: normal;
    overflow-wrap: anywhere;
}
div[data-baseweb="select"] > div {
    background: #151a1b !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 4px !important;
    box-shadow: none !important;
}
.smop-hero,
.smop-notice {
    display: none;
}
.cmd-topbar {
    min-height: 3.3rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: .68rem .9rem;
    margin: -.85rem -1rem 1rem -1rem;
    background: linear-gradient(180deg, rgba(15, 17, 17, .99), rgba(5, 7, 7, .98));
    border-bottom: 1px solid rgba(255, 255, 255, .08);
    border-radius: 4px;
    box-shadow: 0 14px 28px rgba(0,0,0,.34);
}
.cmd-brand {
    display: flex;
    align-items: center;
    gap: .9rem;
    color: #7af24b;
    font-size: .92rem;
    font-weight: 800;
    letter-spacing: .03em;
}
.cmd-menu {
    width: 1.4rem;
    height: 1.4rem;
    display: inline-flex;
    flex-direction: column;
    justify-content: center;
    gap: .22rem;
    color: #c8f8bd;
}
.cmd-menu-line {
    display: block;
    width: 1rem;
    height: .12rem;
    border-radius: 999px;
    background: #a9f49a;
}
.cmd-live {
    display: inline-flex;
    align-items: center;
    height: 1.55rem;
    padding: 0 .78rem;
    border-radius: 999px;
    color: #09150b;
    background: linear-gradient(180deg, #6fd347, #3e982d);
    font-size: .76rem;
    font-weight: 850;
}
.cmd-top-meta {
    display: flex;
    align-items: center;
    gap: .72rem;
    color: rgba(236, 244, 235, .76);
    font-size: .82rem;
}
.cmd-select {
    padding: .35rem .65rem;
    min-width: 5.6rem;
    border-radius: 4px;
    background: #1a2021;
    border: 1px solid rgba(255,255,255,.08);
    color: #e8f0e8;
}
.cmd-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    gap: 1rem;
    align-items: start;
}
.cmd-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .72rem;
    margin-bottom: .85rem;
}
.cmd-kpi-card,
.cmd-panel,
.cmd-inspector {
    background:
        radial-gradient(circle at 50% -28%, rgba(103, 227, 74, .04), transparent 9rem),
        linear-gradient(180deg, rgba(24, 29, 29, .985), rgba(11, 14, 15, .995));
    border: 1px solid rgba(255, 255, 255, .095);
    border-radius: 4px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.045), 0 20px 38px rgba(0,0,0,.28);
}
.cmd-kpi-card {
    min-height: 8.4rem;
    padding: .95rem 1rem .8rem;
    display: flex;
    flex-direction: column;
    gap: .15rem;
}
.cmd-kpi-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: .62rem;
}
.cmd-kpi-head .trust-badge-row {
    justify-content: flex-end;
    margin-top: 0;
    flex-shrink: 0;
}
.cmd-label,
.cmd-panel-title,
.cmd-inspector-title {
    color: #eaf4e9;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .025em;
    text-transform: uppercase;
    line-height: 1.28;
}
.cmd-kpi-value {
    color: #f3f6f3;
    font-size: 1.78rem;
    font-weight: 820;
    line-height: 1.08;
    margin-top: .42rem;
    overflow-wrap: anywhere;
}
.cmd-kpi-sub {
    color: #70e44e;
    font-size: .78rem;
    margin-top: .42rem;
    min-height: 2.15rem;
    line-height: 1.38;
    overflow-wrap: anywhere;
}
.cmd-muted {
    color: rgba(224, 231, 224, .62);
}
.cmd-panels-2 {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr);
    gap: .6rem;
    margin-bottom: .6rem;
}
.cmd-panels-3 {
    display: grid;
    grid-template-columns: .78fr .92fr .92fr .92fr;
    gap: .6rem;
    margin-top: .6rem;
}
.cmd-panel {
    min-height: 15rem;
    padding: 1rem;
    overflow: hidden;
}
.cmd-panel.compact {
    min-height: 11rem;
}
.cmd-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .7rem;
    flex-wrap: wrap;
    margin-bottom: .75rem;
}
.cmd-decision-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.16fr) minmax(25rem, .84fr);
    gap: .72rem;
    align-items: start;
    margin-bottom: .72rem;
}
.cmd-risk-row {
    display: grid;
    grid-template-columns: minmax(6.7rem, .9fr) minmax(4.5rem, 1fr) 2.4rem 3.3rem;
    gap: .62rem;
    align-items: center;
    margin: .68rem 0;
    color: #f2f6f2;
    font-size: .81rem;
}
.cmd-risk-decision-list {
    display: grid;
    gap: .52rem;
}
.cmd-risk-decision-row {
    display: grid;
    grid-template-columns: 2rem minmax(0, 1fr) 3.4rem;
    gap: .62rem;
    align-items: center;
    padding: .66rem .72rem;
    border: 1px solid rgba(255,255,255,.075);
    border-left: 3px solid #6ee047;
    border-radius: 3px;
    background: rgba(255,255,255,.018);
}
.cmd-risk-decision-row.medium {
    border-left-color: #f4ce31;
}
.cmd-risk-decision-row.high {
    border-left-color: #ff8d22;
}
.cmd-risk-decision-row.critical {
    border-left-color: #ff4841;
}
.cmd-risk-rank {
    display: grid;
    place-items: center;
    width: 1.7rem;
    height: 1.7rem;
    border-radius: 3px;
    color: #081008;
    background: #70e44e;
    font-size: .7rem;
    font-weight: 900;
}
.cmd-risk-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .5rem;
    color: #f2f6f2;
    font-size: .82rem;
    font-weight: 820;
    line-height: 1.25;
}
.cmd-risk-meta {
    margin-top: .24rem;
    color: rgba(234,244,233,.62);
    font-size: .72rem;
    line-height: 1.4;
}
.cmd-risk-score {
    text-align: right;
    color: #f2f6f2;
    font-size: 1.12rem;
    font-weight: 850;
    line-height: 1.05;
}
.cmd-risk-score small {
    display: block;
    margin-top: .18rem;
    color: rgba(234,244,233,.5);
    font-size: .58rem;
    font-weight: 700;
    text-transform: uppercase;
}
.cmd-bar {
    height: .24rem;
    border-radius: 999px;
    background: rgba(255,255,255,.12);
    overflow: hidden;
}
.cmd-bar-fill {
    height: 100%;
    border-radius: inherit;
}
.cmd-status-low { color: #6ee047; }
.cmd-status-medium { color: #f4ce31; }
.cmd-status-high { color: #ff8d22; }
.cmd-status-critical { color: #ff4841; }
.cmd-matrix {
    display: grid;
    grid-template-columns: 5.15rem 1fr;
    gap: .34rem .48rem;
    align-items: center;
}
.cmd-matrix-label {
    color: rgba(234,244,233,.76);
    font-size: .66rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cmd-matrix-cells {
    display: grid;
    grid-template-columns: repeat(14, minmax(12px, 1fr));
    gap: .16rem;
}
.cmd-cell {
    aspect-ratio: 1.15 / 1;
    border-radius: 1px;
    background: #58c846;
}
.cmd-legend {
    display: flex;
    gap: .7rem;
    flex-wrap: wrap;
    margin-top: .8rem;
    color: rgba(234,244,233,.68);
    font-size: .72rem;
}
.cmd-swatch {
    display: inline-block;
    width: .55rem;
    height: .55rem;
    margin-right: .25rem;
    vertical-align: middle;
}
.cmd-alert-list {
    max-height: 17.8rem;
    overflow: auto;
    padding-right: .25rem;
}
.cmd-alert {
    border-left: 1px solid rgba(255,255,255,.12);
    padding: 0 0 .76rem .78rem;
    margin-bottom: .72rem;
    color: #eef4ee;
}
.cmd-alert-sev {
    display: inline-flex;
    align-items: center;
    gap: .35rem;
    font-size: .76rem;
    font-weight: 850;
    text-transform: uppercase;
}
.cmd-alert-title {
    margin-top: .28rem;
    font-size: .92rem;
    font-weight: 760;
}
.cmd-alert-meta {
    color: rgba(234,244,233,.62);
    font-size: .76rem;
    line-height: 1.45;
}
.cmd-inspector {
    padding: .9rem;
    position: sticky;
    top: 1rem;
    min-height: 48rem;
}
.cmd-inspector-title {
    color: #79ef4d;
    margin-bottom: 1.05rem;
}
.cmd-machine-name {
    color: #f4f7f4;
    font-size: 1.08rem;
    font-weight: 840;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cmd-chip {
    display: inline-block;
    padding: .18rem .45rem;
    border-radius: 3px;
    background: rgba(255, 72, 65, .18);
    color: #ff5c50;
    font-size: .72rem;
    font-weight: 850;
    text-transform: uppercase;
    margin-left: 0;
    margin-top: .42rem;
}
.cmd-chip.stable {
    background: rgba(103, 227, 74, .16);
    color: #7af24b;
}
.cmd-chip.warning {
    background: rgba(244, 206, 49, .16);
    color: #f4ce31;
}
.cmd-chip.critical {
    background: rgba(255, 72, 65, .18);
    color: #ff5c50;
}
.cmd-tabs {
    display: flex;
    gap: .8rem;
    border-bottom: 1px solid rgba(255,255,255,.08);
    margin: 1rem 0 .9rem;
    color: rgba(234,244,233,.65);
    font-size: .68rem;
    text-transform: uppercase;
}
.cmd-tabs span:first-child {
    color: #c7ffb6;
    border-bottom: 2px solid #70e44e;
    padding-bottom: .42rem;
}
.cmd-gauge-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: .55rem;
}
.cmd-ring-card {
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 3px;
    padding: .72rem;
    min-height: 8.3rem;
    background: rgba(255,255,255,.018);
}
.cmd-ring {
    width: 5.2rem;
    height: 5.2rem;
    border-radius: 50%;
    position: relative;
    margin: .52rem auto 0;
    box-shadow: inset 0 0 16px rgba(0,0,0,.45);
}
.cmd-ring::after {
    content: "";
    position: absolute;
    inset: .58rem;
    border-radius: 50%;
    background: #111617;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.045);
}
.cmd-ring-value {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    z-index: 1;
    color: #f2f5f2;
    text-align: center;
    font-weight: 840;
    font-size: 1.08rem;
}
.cmd-ring-value small {
    display: block;
    color: rgba(234,244,233,.58);
    font-size: .64rem;
    font-weight: 650;
}
.cmd-mini {
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 3px;
    padding: .75rem;
    min-height: 7.5rem;
    background: rgba(255,255,255,.018);
}
.cmd-mini-value {
    color: #f2f5f2;
    font-size: 1.55rem;
    font-weight: 830;
}
.cmd-mini.danger .cmd-mini-value { color: #ff4c43; }
.cmd-telemetry {
    margin-top: .8rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 3px;
    padding: .75rem;
}
.cmd-telemetry-row {
    display: grid;
    grid-template-columns: minmax(5.4rem, 1fr) 3.65rem 3.9rem;
    gap: .34rem;
    align-items: center;
    min-height: 1.72rem;
    color: #f1f5f0;
    font-size: .72rem;
}
.cmd-telemetry-row span:first-child {
    color: rgba(234,244,233,.68);
}
.cmd-telemetry-value {
    color: #f2f6f2;
    font-weight: 780;
    line-height: 1.15;
}
.cmd-telemetry-value small {
    display: block;
    margin-top: .12rem;
    color: rgba(234,244,233,.48);
    font-size: .58rem;
    font-weight: 650;
    white-space: nowrap;
}
.cmd-lineage {
    margin-top: .75rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 3px;
    padding: .72rem;
    background: rgba(255,255,255,.018);
}
.cmd-lineage-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: .55rem;
    align-items: baseline;
    padding: .38rem 0;
    border-bottom: 1px solid rgba(255,255,255,.055);
    color: rgba(234,244,233,.67);
    font-size: .72rem;
}
.cmd-lineage-row:last-child {
    border-bottom: 0;
}
.cmd-lineage-row strong {
    max-width: 8.6rem;
    color: #f2f6f2;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cmd-driver-row {
    margin-top: .58rem;
}
.cmd-driver-meta {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: .5rem;
    color: rgba(234,244,233,.72);
    font-size: .7rem;
}
.cmd-driver-bar {
    height: .28rem;
    margin-top: .24rem;
    border-radius: 999px;
    background: rgba(255,255,255,.08);
    overflow: hidden;
}
.cmd-driver-bar span {
    display: block;
    height: 100%;
    border-radius: inherit;
}
.cmd-action-tile {
    border: 1px solid rgba(112, 228, 78, .22);
    border-radius: 3px;
    padding: .62rem .58rem;
    color: #eaf4e9;
    background: rgba(255,255,255,.018);
    font-size: .72rem;
}
.cmd-action-tile strong {
    display: block;
    margin-bottom: .18rem;
    color: #9dfc77;
    font-size: .76rem;
}
.cmd-action-list {
    display: grid;
    gap: .48rem;
    margin-top: .75rem;
}
.cmd-action-row {
    display: grid;
    grid-template-columns: 4.1rem minmax(0, 1.02fr) minmax(0, 1.08fr);
    gap: .72rem;
    align-items: start;
    padding: .7rem .75rem;
    border: 1px solid rgba(255,255,255,.075);
    border-left: 3px solid #67e34a;
    border-radius: 3px;
    background: rgba(255,255,255,.018);
    color: #eef4ee;
}
.cmd-action-row.warn {
    border-left-color: #f4ce31;
}
.cmd-action-row.risk {
    border-left-color: #ff5148;
}
.cmd-priority-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.7rem;
    height: 1.8rem;
    border-radius: 3px;
    background: rgba(103, 227, 74, .14);
    color: #78f24d;
    font-size: .76rem;
    font-weight: 900;
}
.cmd-action-row.warn .cmd-priority-badge {
    background: rgba(244, 206, 49, .16);
    color: #f4ce31;
}
.cmd-action-row.risk .cmd-priority-badge {
    background: rgba(255, 72, 65, .16);
    color: #ff5c50;
}
.cmd-action-main {
    font-weight: 830;
    line-height: 1.28;
}
.cmd-action-sub {
    color: rgba(234,244,233,.64);
    font-size: .76rem;
    line-height: 1.45;
}
.cmd-action-meta {
    display: flex;
    flex-wrap: wrap;
    gap: .32rem .55rem;
    margin-top: .35rem;
    color: rgba(234,244,233,.58);
    font-size: .68rem;
    line-height: 1.35;
}
.cmd-action-decision {
    color: #f2f6f2;
    font-size: .8rem;
    font-weight: 760;
    line-height: 1.36;
}
.cmd-workflow-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .6rem;
    margin: .75rem 0;
}
.cmd-workflow-board {
    display: grid;
    grid-template-columns: repeat(6, minmax(11rem, 1fr));
    gap: .55rem;
    align-items: start;
    margin-top: .75rem;
}
.cmd-workflow-lane {
    min-height: 16rem;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 4px;
    padding: .68rem;
    background: rgba(255,255,255,.018);
}
.cmd-workflow-lane-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #eaf4e9;
    font-size: .72rem;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: .02em;
    margin-bottom: .55rem;
}
.cmd-case-card {
    border: 1px solid rgba(255,255,255,.085);
    border-left: 3px solid #67e34a;
    border-radius: 3px;
    padding: .62rem;
    background: rgba(6, 10, 10, .64);
    color: #eef4ee;
    margin-bottom: .5rem;
}
.cmd-case-card.high,
.cmd-case-card.critical {
    border-left-color: #ff5148;
}
.cmd-case-card.medium {
    border-left-color: #f2cb28;
}
.cmd-case-title {
    font-size: .79rem;
    font-weight: 800;
    line-height: 1.3;
}
.cmd-case-meta {
    margin-top: .32rem;
    color: rgba(234,244,233,.6);
    font-size: .66rem;
    line-height: 1.42;
}
.cmd-case-chip {
    display: inline-flex;
    margin-top: .38rem;
    padding: .12rem .38rem;
    border-radius: 3px;
    font-size: .62rem;
    font-weight: 850;
    text-transform: uppercase;
    background: rgba(103, 227, 74, .14);
    color: #78f24d;
}
.cmd-case-chip.high,
.cmd-case-chip.critical {
    background: rgba(255, 72, 65, .16);
    color: #ff5c50;
}
.cmd-case-chip.medium {
    background: rgba(244, 206, 49, .16);
    color: #f4ce31;
}
.cmd-workflow-detail {
    display: grid;
    grid-template-columns: minmax(0, .95fr) minmax(0, 1.2fr);
    gap: .7rem;
    margin-top: .75rem;
}
.cmd-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: .6rem;
    margin-top: .8rem;
}
.cmd-btn {
    display: block;
    text-align: center;
    border: 1px solid rgba(112, 228, 78, .45);
    border-radius: 3px;
    padding: .62rem .5rem;
    color: #9dfc77;
    font-weight: 760;
    font-size: .78rem;
}
.cmd-btn.primary {
    background: #67d343;
    color: #081008;
    border-color: #67d343;
}
.cmd-list-row {
    display: grid;
    grid-template-columns: minmax(7rem, 1fr) 3.5rem 5.2rem;
    gap: .7rem;
    align-items: center;
    color: #eef4ee;
    font-size: .78rem;
    margin: .58rem 0;
}
.cmd-small-spark svg {
    width: 100%;
    height: 24px;
}
.cmd-kpi-card > .cmd-small-spark {
    display: block;
    margin-top: auto;
}
.cmd-donut-wrap {
    display: grid;
    grid-template-columns: 9rem 1fr;
    gap: 1.15rem;
    align-items: center;
}
.cmd-donut {
    width: 8.2rem;
    height: 8.2rem;
    border-radius: 50%;
    position: relative;
    box-shadow: inset 0 0 20px rgba(0,0,0,.38);
}
.cmd-donut::after {
    content: "";
    position: absolute;
    inset: 1.95rem;
    border-radius: 50%;
    background: #121719;
    box-shadow: 0 0 0 1px rgba(255,255,255,.05);
}
.cmd-donut-center {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    z-index: 1;
    color: #f2f6f2;
    text-align: center;
    font-weight: 830;
}
.cmd-donut-center small {
    display: block;
    color: rgba(234,244,233,.64);
    font-size: .7rem;
    font-weight: 650;
}
.cmd-progress {
    height: .25rem;
    border-radius: 999px;
    background: rgba(255,255,255,.1);
    overflow: hidden;
}
.cmd-progress > span {
    display: block;
    height: 100%;
    border-radius: inherit;
}
@media (max-width: 1200px) {
    .cmd-main-grid,
    .cmd-panels-2,
    .cmd-panels-3 {
        grid-template-columns: 1fr;
    }
    .cmd-kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .cmd-inspector {
        position: static;
        min-height: 0;
    }
}
@media (max-width: 1500px) {
    .cmd-kpi-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .cmd-kpi-card {
        min-height: 8rem;
    }
    .cmd-kpi-value {
        font-size: 1.62rem;
    }
    .cmd-label {
        font-size: .69rem;
    }
}
@media (max-width: 1700px) {
    .cmd-panels-2 {
        grid-template-columns: minmax(0, 1.04fr) minmax(0, .96fr);
    }
    .cmd-panels-3 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .cmd-workflow-board {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}
@media (max-width: 1350px) {
    .cmd-decision-grid,
    .cmd-panels-2,
    .cmd-panels-3 {
        grid-template-columns: 1fr;
    }
    .cmd-inspector {
        position: static;
        min-height: 0;
    }
    .cmd-workflow-detail {
        grid-template-columns: 1fr;
    }
    .cmd-workflow-board {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .cmd-workflow-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .cmd-kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 760px) {
    .block-container {
        padding-left: .7rem;
        padding-right: .7rem;
    }
    .cmd-topbar {
        align-items: flex-start;
        flex-direction: column;
        gap: .55rem;
        margin: -.55rem -.5rem 1rem -.5rem;
        padding: .72rem .8rem;
    }
    .cmd-brand {
        max-width: 100%;
        gap: .55rem;
        font-size: .82rem;
        line-height: 1.35;
    }
    .cmd-top-meta {
        width: 100%;
        flex-wrap: wrap;
        gap: .45rem;
        font-size: .72rem;
    }
    .cmd-select {
        min-width: 0;
        padding: .3rem .5rem;
    }
    .cmd-kpi-grid,
    .cmd-workflow-grid,
    .cmd-workflow-board {
        grid-template-columns: 1fr;
    }
    .cmd-kpi-card {
        min-height: 9.8rem;
        padding: .95rem;
    }
    .cmd-kpi-head {
        gap: .45rem;
    }
    .cmd-kpi-head .trust-badge-row {
        max-width: 9.5rem;
    }
    .cmd-kpi-value {
        font-size: 1.55rem;
    }
    .cmd-kpi-sub {
        min-height: 0;
    }
    .cmd-panel {
        min-height: auto;
        padding: .85rem;
    }
    .cmd-action-row {
        grid-template-columns: 1fr;
        gap: .45rem;
    }
    .cmd-risk-decision-row {
        grid-template-columns: 1.85rem minmax(0, 1fr);
    }
    .cmd-risk-score {
        grid-column: 2;
        text-align: left;
        font-size: .95rem;
    }
    .cmd-risk-score small {
        display: inline;
        margin-left: .22rem;
    }
    .cmd-risk-row {
        grid-template-columns: minmax(5.6rem, .9fr) minmax(4rem, 1fr) 2rem 3.1rem;
        gap: .38rem;
        font-size: .74rem;
    }
    .cmd-matrix {
        grid-template-columns: 4.8rem 1fr;
    }
    .cmd-matrix-cells {
        grid-template-columns: repeat(14, minmax(7px, 1fr));
        gap: .12rem;
    }
    .cmd-legend {
        gap: .5rem;
        font-size: .66rem;
    }
    [data-testid="stMetric"] {
        min-height: 5.25rem;
        padding: .65rem .75rem;
    }
    [data-testid="stMetricLabel"] {
        min-height: auto;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    .metric-trust-card {
        min-height: 5.25rem;
        padding: .64rem .72rem;
    }
    .metric-trust-head {
        min-height: auto;
        align-items: center;
    }
    .metric-trust-label {
        font-size: .72rem;
    }
    .metric-trust-value {
        font-size: 1.45rem;
    }
    div[data-testid="stPlotlyChart"] {
        padding: .28rem .28rem .05rem;
    }
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


def render_metric_with_trust(container: Any, label: str, value: Any, trust_level: str, lang: str) -> None:
    """Render a compact metric card with the trust badge inside the same visual unit."""
    container.markdown(
        '<div class="metric-trust-card">'
        '<div class="metric-trust-head">'
        f'<span class="metric-trust-label">{escape(str(label))}</span>'
        f'{trust_badge_html(trust_level, lang)}'
        '</div>'
        f'<div class="metric-trust-value">{escape(str(value))}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def status_pill(label: str, tone: str = "info") -> str:
    """Return a status pill as HTML."""
    safe_label = escape(str(label))
    safe_tone = tone if tone in {"ok", "warn", "risk", "info"} else "info"
    return f'<span class="smop-pill smop-pill-{safe_tone}">{safe_label}</span>'


def render_status_pills(items: list[tuple[str, str]]) -> None:
    """Render multiple status pills on one line."""
    st.markdown(" ".join(status_pill(label, tone) for label, tone in items), unsafe_allow_html=True)


def render_notice(title: str, body: str, detail: str = "") -> None:
    """Render a compact operational notice."""
    detail_html = f'<div class="smop-card-caption">{escape(detail)}</div>' if detail else ""
    st.markdown(
        '<div class="smop-notice">'
        f'<div class="smop-notice-title">{escape(title)}</div>'
        f'<div>{escape(body)}</div>{detail_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def sensor_value(row: pd.Series, column: str) -> float | None:
    """Read a numeric sensor value from a row."""
    value = row.get(column)
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Clamp a value into a fixed range."""
    return max(lower, min(upper, value))


def derive_condition_score(row: pd.Series) -> float:
    """Derive a transparent machine condition score from sensor columns."""
    vibration = sensor_value(row, "vibration_rms") or 0.0
    wear = sensor_value(row, "tool_wear") or 0.0
    temp = sensor_value(row, "process_temperature") or 0.0
    current = sensor_value(row, "motor_current") or 0.0
    torque = sensor_value(row, "torque") or 0.0

    vibration_penalty = clamp((vibration - 1.1) / 2.4 * 34.0)
    wear_penalty = clamp(wear / 100.0 * 28.0)
    temp_penalty = clamp(max(0.0, temp - 58.0) / 22.0 * 16.0)
    current_penalty = clamp(max(0.0, current - 8.0) / 12.0 * 12.0)
    torque_penalty = clamp(max(0.0, torque - 18.0) / 18.0 * 10.0)
    return round(clamp(100.0 - vibration_penalty - wear_penalty - temp_penalty - current_penalty - torque_penalty), 1)


def derive_anomaly_index(row: pd.Series) -> float:
    """Derive a transparent anomaly index from the same sensor evidence."""
    return round(clamp(100.0 - derive_condition_score(row)) / 100.0, 3)


def risk_from_score(score: float, lang: str) -> tuple[str, str]:
    """Convert a condition score into a localized risk label and tone."""
    if score < 45:
        return t(lang, "risk_critical"), "risk"
    if score < 62:
        return t(lang, "risk_high"), "risk"
    if score < 78:
        return t(lang, "risk_elevated"), "warn"
    return t(lang, "risk_normal"), "ok"


def dominant_signal(row: pd.Series, lang: str) -> str:
    """Return the sensor dimension contributing the strongest concern."""
    candidates = {
        t(lang, "signal_vibration"): (sensor_value(row, "vibration_rms") or 0.0) / 3.4,
        t(lang, "signal_tool_wear"): (sensor_value(row, "tool_wear") or 0.0) / 100.0,
        t(lang, "signal_temperature"): max(0.0, (sensor_value(row, "process_temperature") or 0.0) - 58.0) / 22.0,
        t(lang, "signal_motor_current"): max(0.0, (sensor_value(row, "motor_current") or 0.0) - 8.0) / 12.0,
        t(lang, "signal_torque"): max(0.0, (sensor_value(row, "torque") or 0.0) - 18.0) / 18.0,
    }
    name, value = max(candidates.items(), key=lambda item: item[1])
    return name if value > 0.1 else t(lang, "signal_balanced")


def signal_driver_scores(row: pd.Series, lang: str) -> list[tuple[str, float, str]]:
    """Return normalized signal-driver scores from the selected sensor row."""
    values = [
        (t(lang, "signal_vibration"), clamp(((sensor_value(row, "vibration_rms") or 0.0) - 1.1) / 2.4 * 100.0), format_metric(sensor_value(row, "vibration_rms"), " mm/s", decimals=2, lang=lang)),
        (t(lang, "signal_tool_wear"), clamp((sensor_value(row, "tool_wear") or 0.0), 0.0, 100.0), format_metric(sensor_value(row, "tool_wear"), "%", decimals=1, lang=lang)),
        (t(lang, "signal_temperature"), clamp(max(0.0, (sensor_value(row, "process_temperature") or 0.0) - 58.0) / 22.0 * 100.0), format_metric(sensor_value(row, "process_temperature"), " C", decimals=1, lang=lang)),
        (t(lang, "signal_motor_current"), clamp(max(0.0, (sensor_value(row, "motor_current") or 0.0) - 8.0) / 12.0 * 100.0), format_metric(sensor_value(row, "motor_current"), " A", decimals=2, lang=lang)),
        (t(lang, "signal_torque"), clamp(max(0.0, (sensor_value(row, "torque") or 0.0) - 18.0) / 18.0 * 100.0), format_metric(sensor_value(row, "torque"), " Nm", decimals=1, lang=lang)),
    ]
    return sorted(values, key=lambda item: item[1], reverse=True)


def driver_color(score: float) -> str:
    """Return visual color for a normalized signal driver."""
    if score >= 70:
        return "#ff5148"
    if score >= 45:
        return "#f0811c"
    if score >= 24:
        return "#f2cb28"
    return "#67e34a"


def format_timestamp_short(value: Any, lang: str) -> str:
    """Return a compact timestamp for inspector metadata."""
    if value is None or pd.isna(value):
        return t(lang, "na")
    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def baseline_delta_text(df: pd.DataFrame, column: str, current: float | None, lang: str, suffix: str = "") -> str:
    """Return current-vs-recent-baseline text for telemetry rows."""
    if current is None or df.empty or column not in df.columns:
        return t(lang, "na")
    baseline = pd.to_numeric(df[column], errors="coerce").dropna().tail(60).mean()
    if pd.isna(baseline):
        return t(lang, "na")
    delta = float(current) - float(baseline)
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f}{suffix} {t(lang, 'baseline_delta')}"


def build_machine_snapshot(sensor: pd.DataFrame, production: pd.DataFrame, predictions: pd.DataFrame, lang: str) -> pd.DataFrame:
    """Build one current operating row per machine from database records."""
    if sensor.empty or "machine_id" not in sensor.columns:
        return pd.DataFrame()

    latest_sensor = latest_by_group(sensor, ["machine_id"], "timestamp").copy()
    latest_predictions = latest_by_group(predictions, ["machine_id"], "timestamp") if not predictions.empty else pd.DataFrame()
    latest_production = latest_by_group(production, ["line_id", "station_id"], "timestamp") if not production.empty else pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, sensor_row in latest_sensor.iterrows():
        machine_id = sensor_row.get("machine_id", t(lang, "na"))
        line_id = sensor_row.get("line_id", t(lang, "na"))
        station_id = sensor_row.get("station_id", t(lang, "na"))
        pred_row = pd.Series(dtype=object)
        if not latest_predictions.empty and "machine_id" in latest_predictions.columns:
            matches = latest_predictions[latest_predictions["machine_id"] == machine_id]
            if not matches.empty:
                pred_row = matches.iloc[-1]

        prod_row = pd.Series(dtype=object)
        if not latest_production.empty and {"line_id", "station_id"} <= set(latest_production.columns):
            prod_matches = latest_production[
                (latest_production["line_id"] == line_id)
                & (latest_production["station_id"] == station_id)
            ]
            if not prod_matches.empty:
                prod_row = prod_matches.iloc[-1]

        derived_score = derive_condition_score(sensor_row)
        condition_score = sensor_value(pred_row, "health_score") if not pred_row.empty else None
        condition_score = round(condition_score, 1) if condition_score is not None else derived_score
        risk_label, risk_tone = risk_from_score(condition_score, lang)
        anomaly_index = sensor_value(pred_row, "anomaly_score") if not pred_row.empty else None
        if anomaly_index is None:
            anomaly_index = derive_anomaly_index(sensor_row)

        rows.append(
            {
                "machine_id": machine_id,
                "line_id": line_id,
                "station_id": station_id,
                "line_station": f"{line_id} / {station_id}",
                "timestamp": sensor_row.get("timestamp"),
                "condition_score": condition_score,
                "derived_anomaly_index": round(float(anomaly_index), 3),
                "risk_level": risk_label,
                "risk_tone": risk_tone,
                "dominant_signal": dominant_signal(sensor_row, lang),
                "vibration_rms": sensor_value(sensor_row, "vibration_rms"),
                "tool_wear": sensor_value(sensor_row, "tool_wear"),
                "process_temperature": sensor_value(sensor_row, "process_temperature"),
                "motor_current": sensor_value(sensor_row, "motor_current"),
                "torque": sensor_value(sensor_row, "torque"),
                "cycle_time_sec": sensor_value(prod_row, "cycle_time_sec") if not prod_row.empty else None,
                "station_yield": sensor_value(prod_row, "station_yield") if not prod_row.empty else None,
                "defect_rate": sensor_value(prod_row, "defect_rate") if not prod_row.empty else None,
                "source": "model+sensor" if not pred_row.empty else "sensor-derived",
            }
        )
    return pd.DataFrame(rows).sort_values(["line_id", "machine_id"])


def build_condition_timeline(sensor: pd.DataFrame, machine_id: str | None = None, limit: int = 300) -> pd.DataFrame:
    """Build a recent condition timeline from sensor records."""
    if sensor.empty or "timestamp" not in sensor.columns:
        return pd.DataFrame()
    source = sensor.copy()
    if machine_id and "machine_id" in source.columns:
        source = source[source["machine_id"] == machine_id]
    if source.empty:
        return pd.DataFrame()
    source = source.sort_values("timestamp").tail(limit).copy()
    source["condition_score"] = source.apply(derive_condition_score, axis=1)
    source["derived_anomaly_index"] = source.apply(derive_anomaly_index, axis=1)
    return source


def render_health_heatmap(snapshot: pd.DataFrame, lang: str) -> None:
    """Render the machine health matrix."""
    st.subheader(t(lang, "machine_health_map"))
    st.caption(t(lang, "machine_health_map_caption"))
    if snapshot.empty:
        show_empty(t(lang, "machine_matrix_empty"))
        return

    if go is not None:
        matrix = snapshot.pivot_table(
            index="line_id",
            columns="machine_id",
            values="condition_score",
            aggfunc="mean",
        )
        fig = go.Figure(
            data=go.Heatmap(
                z=matrix.values,
                x=matrix.columns.tolist(),
                y=matrix.index.tolist(),
                zmin=0,
                zmax=100,
                colorscale=[
                    [0.0, "#a61616"],
                    [0.42, "#d5a026"],
                    [0.68, "#9edb57"],
                    [1.0, "#36c95f"],
                ],
                hovertemplate="%{y}<br>%{x}<br>%{z:.1f}<extra></extra>",
                colorbar=dict(title=t(lang, "condition_score")),
            )
        )
        fig.update_layout(
            height=300,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=8, r=8, t=18, b=8),
            font=dict(color="#eaf4ed", size=12),
            xaxis=dict(side="top", gridcolor="rgba(116,217,67,.12)"),
            yaxis=dict(gridcolor="rgba(116,217,67,.12)"),
        )
        st.plotly_chart(fig, width="stretch")
    else:
        display_dataframe(
            snapshot[["machine_id", "line_station", "condition_score", "risk_level", "dominant_signal"]],
            lang,
            width="stretch",
            hide_index=True,
        )


def render_condition_timeline(timeline: pd.DataFrame, lang: str, title_key: str = "anomaly_timeline_derived") -> None:
    """Render the condition drift timeline."""
    st.subheader(t(lang, title_key))
    st.caption(t(lang, "anomaly_timeline_caption"))
    if timeline.empty:
        show_empty(t(lang, "no_machine_stream"))
        return
    if px is not None:
        fig = px.scatter(
            timeline,
            x="timestamp",
            y="derived_anomaly_index",
            color="machine_id" if "machine_id" in timeline.columns else None,
            size="condition_score",
            hover_data=[c for c in ["line_id", "station_id", "vibration_rms", "tool_wear", "process_temperature"] if c in timeline.columns],
            title="",
        )
        fig.update_layout(
            height=330,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=8, r=8, t=12, b=8),
            font=dict(color="#eaf4ed", size=12),
            yaxis_title=t(lang, "derived_anomaly_index"),
            xaxis_title="",
            legend_title_text="",
        )
        fig.update_traces(marker=dict(opacity=.8, line=dict(width=.5, color="rgba(255,255,255,.55)")))
        st.plotly_chart(fig, width="stretch")
    else:
        cols = [c for c in ["timestamp", "machine_id", "condition_score", "derived_anomaly_index", "vibration_rms", "tool_wear"] if c in timeline.columns]
        display_dataframe(timeline[cols].tail(80), lang, width="stretch", hide_index=True)


def render_machine_inspector(
    snapshot: pd.DataFrame,
    sensor: pd.DataFrame,
    production: pd.DataFrame,
    lang: str,
    key_prefix: str,
) -> str | None:
    """Render a machine inspector and return the selected machine."""
    st.markdown(
        '<div class="smop-inspector">'
        f'<div class="smop-inspector-title">{escape(t(lang, "investigation_panel"))}</div>'
        f'<div class="smop-inspector-caption">{escape(t(lang, "investigation_panel_caption"))}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if snapshot.empty:
        show_empty(t(lang, "machine_matrix_empty"))
        return None

    machines = snapshot["machine_id"].dropna().astype(str).tolist()
    selected_machine = st.selectbox(t(lang, "select_machine_for_deep_dive"), machines, key=f"{key_prefix}_machine")
    selected = snapshot[snapshot["machine_id"] == selected_machine].iloc[0]
    risk_label = selected.get("risk_level", t(lang, "na"))
    risk_tone = selected.get("risk_tone", "info")
    render_status_pills([(str(risk_label), str(risk_tone)), (str(selected.get("source", "")), "info")])

    st.markdown(
        '<div class="smop-kv">'
        f'<div class="smop-kv-item"><div class="smop-kv-label">{escape(t(lang, "condition_score"))}</div><div class="smop-kv-value">{escape(format_metric(selected.get("condition_score"), decimals=1, lang=lang))}</div></div>'
        f'<div class="smop-kv-item"><div class="smop-kv-label">{escape(t(lang, "derived_anomaly_index"))}</div><div class="smop-kv-value">{escape(format_metric(selected.get("derived_anomaly_index"), decimals=3, lang=lang))}</div></div>'
        f'<div class="smop-kv-item"><div class="smop-kv-label">{escape(t(lang, "dominant_signal"))}</div><div class="smop-kv-value">{escape(str(selected.get("dominant_signal", t(lang, "na"))))}</div></div>'
        f'<div class="smop-kv-item"><div class="smop-kv-label">{escape(t(lang, "line_station"))}</div><div class="smop-kv-value">{escape(str(selected.get("line_station", t(lang, "na"))))}</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption(t(lang, "showing_database_records"))

    selected_sensor = sensor[sensor["machine_id"] == selected_machine].copy() if "machine_id" in sensor.columns else pd.DataFrame()
    selected_production = pd.DataFrame()
    if not production.empty and {"line_id", "station_id"} <= set(production.columns):
        selected_production = production[
            (production["line_id"] == selected.get("line_id"))
            & (production["station_id"] == selected.get("station_id"))
        ].copy()

    c1, c2 = st.columns(2)
    render_metric_with_trust(c1, t(lang, "source_records"), t(lang, "sensor_record_count", value=f"{len(selected_sensor):,}"), TRUST_LIVE, lang)
    render_metric_with_trust(c2, t(lang, "operating_context"), t(lang, "production_record_count", value=f"{len(selected_production):,}"), TRUST_LIVE, lang)
    return selected_machine


def sparkline_svg(values: list[float], stroke: str = "#67e34a", fill: str = "rgba(103, 227, 74, .16)") -> str:
    """Return a compact inline SVG sparkline."""
    clean = [float(v) for v in values if v is not None and not pd.isna(v)]
    if len(clean) < 2:
        clean = [0.0, 0.0]
    clean = clean[-32:]
    low = min(clean)
    high = max(clean)
    span = high - low or 1.0
    points: list[tuple[float, float]] = []
    for index, value in enumerate(clean):
        x = index / max(1, len(clean) - 1) * 110.0
        y = 24.0 - ((value - low) / span * 20.0 + 2.0)
        points.append((x, y))
    path = " ".join(("M" if idx == 0 else "L") + f"{x:.2f},{y:.2f}" for idx, (x, y) in enumerate(points))
    fill_path = f"{path} L 110,28 L 0,28 Z"
    return (
        '<svg viewBox="0 0 110 30" preserveAspectRatio="none" aria-hidden="true">'
        f'<path d="{fill_path}" fill="{escape(fill)}"></path>'
        f'<path d="{path}" fill="none" stroke="{escape(stroke)}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>'
        '</svg>'
    )


def command_metric_card(
    title: str,
    value: str,
    sub: str,
    spark_values: list[float] | None = None,
    tone: str = "ok",
    trust_levels: list[str] | None = None,
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """Return one command-center KPI card."""
    stroke = {"ok": "#67e34a", "warn": "#f4ce31", "risk": "#ff5148", "info": "#36d8d0"}.get(tone, "#67e34a")
    spark = sparkline_svg(spark_values or [0, 1, 0.7, 1.3], stroke=stroke)
    trust_html = trust_badges_html(trust_levels or [TRUST_DERIVED], lang)
    return (
        '<div class="cmd-kpi-card">'
        '<div class="cmd-kpi-head">'
        f'<div class="cmd-label">{escape(title)}</div>'
        f'{trust_html}'
        '</div>'
        f'<div class="cmd-kpi-value">{escape(value)}</div>'
        f'<div class="cmd-kpi-sub">{escape(sub)}</div>'
        f'<div class="cmd-small-spark">{spark}</div>'
        '</div>'
    )


def risk_css_from_score(score: float, lang: str = DEFAULT_LANGUAGE) -> tuple[str, str, str]:
    """Return risk label, class, and color from a 0-100 risk score."""
    if score >= 80:
        return t(lang, "risk_critical"), "critical", "#ff4841"
    if score >= 60:
        return t(lang, "risk_high"), "high", "#ff8d22"
    if score >= 40:
        return t(lang, "risk_elevated"), "medium", "#f4ce31"
    return t(lang, "risk_low"), "low", "#6ee047"


def severity_score(severity: Any) -> int:
    """Map stored severity strings to a numeric risk score."""
    return {"low": 20, "medium": 50, "high": 70, "critical": 90}.get(str(severity).lower(), 40)


def condition_color(score: float) -> str:
    """Map condition score to matrix cell color."""
    if score < 25:
        return "#d83a32"
    if score < 45:
        return "#f0781d"
    if score < 62:
        return "#f1cf2d"
    if score < 82:
        return "#6fd346"
    return "#45a236"


def latest_numeric_values(df: pd.DataFrame, column: str, limit: int = 32) -> list[float]:
    """Return recent numeric values for a sparkline."""
    if df.empty or column not in df.columns:
        return []
    return pd.to_numeric(df.sort_values("timestamp")[column], errors="coerce").dropna().tail(limit).tolist()


def priority_groups_for_chart(df: pd.DataFrame, group_col: str, limit: int = 2) -> list[str]:
    """Return the groups most worth showing when an all-station chart would be noisy."""
    if df.empty or group_col not in df.columns:
        return []
    source = df.copy()
    scores: list[tuple[str, float]] = []
    for group_id, group_df in source.groupby(group_col, dropna=False):
        score = 0.0
        if "cycle_time_sec" in group_df.columns:
            score += max(0.0, (safe_mean(group_df, "cycle_time_sec") or 0.0) - 5.5) * 12.0
        if "downtime_minutes" in group_df.columns:
            score += float(pd.to_numeric(group_df["downtime_minutes"], errors="coerce").fillna(0.0).sum()) * 1.8
        if "defect_rate" in group_df.columns:
            score += (safe_mean(group_df, "defect_rate") or 0.0) * 240.0
        elif "reject_count" in group_df.columns:
            score += float(pd.to_numeric(group_df["reject_count"], errors="coerce").fillna(0.0).sum()) * .4
        if "station_yield" in group_df.columns:
            score += max(0.0, .98 - (safe_mean(group_df, "station_yield") or .98)) * 160.0
        scores.append((str(group_id), score))
    if not scores:
        return []
    return [group for group, _ in sorted(scores, key=lambda item: item[1], reverse=True)[:limit]]


def format_alert_time(value: Any) -> str:
    """Return a compact time label for alert rows."""
    if value is None or pd.isna(value):
        return ""
    try:
        return pd.Timestamp(value).strftime("%H:%M:%S")
    except Exception:
        text = str(value)
        return text[-8:] if len(text) > 8 else text


def build_command_alerts(alerts: pd.DataFrame, timeline: pd.DataFrame, lang: str, limit: int = 6) -> list[dict[str, Any]]:
    """Build alert rows from model alerts or sensor-derived anomaly signals."""
    rows: list[dict[str, Any]] = []
    if not alerts.empty:
        for _, row in alerts.sort_values("timestamp", ascending=False).head(limit).iterrows():
            severity = str(row.get("severity", "medium")).title()
            rows.append(
                {
                    "severity": severity,
                    "time": format_alert_time(row.get("timestamp")),
                    "machine_id": row.get("machine_id", t(lang, "na")),
                    "title": row.get("message", t(lang, "anomaly_alert_signal", score=row.get("anomaly_score", t(lang, "na")))),
                    "meta": f"{row.get('line_id', t(lang, 'na'))} / {row.get('station_id', t(lang, 'na'))}",
                    "score": row.get("anomaly_score", t(lang, "na")),
                }
            )
    elif not timeline.empty:
        source = timeline.sort_values(["derived_anomaly_index", "timestamp"], ascending=[False, False]).head(limit)
        for _, row in source.iterrows():
            score = float(row.get("derived_anomaly_index", 0.0) or 0.0)
            severity = "Critical" if score >= .65 else "High" if score >= .45 else "Medium" if score >= .25 else "Low"
            rows.append(
                {
                    "severity": severity,
                    "time": format_alert_time(row.get("timestamp")),
                    "machine_id": row.get("machine_id", t(lang, "na")),
                    "title": f"{dominant_signal(row, lang)} {t(lang, 'derived_anomaly_index')}",
                    "meta": f"{row.get('line_id', t(lang, 'na'))} / {row.get('station_id', t(lang, 'na'))}",
                    "score": f"{score:.2f}",
                }
            )
    return rows


def render_command_topbar(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render the command-center top bar."""
    latest_ts = first_available_timestamp(tables, latest=True)
    if latest_ts is not None and not pd.isna(latest_ts):
        update_text = pd.Timestamp(latest_ts).strftime("%H:%M:%S")
        date_format = "%b %d, %Y %H:%M" if lang == DEFAULT_LANGUAGE else "%Y-%m-%d %H:%M"
        date_text = pd.Timestamp(latest_ts).strftime(date_format)
    else:
        update_text = datetime.now().strftime("%H:%M:%S")
        date_format = "%b %d, %Y %H:%M" if lang == DEFAULT_LANGUAGE else "%Y-%m-%d %H:%M"
        date_text = datetime.now().strftime(date_format)
    st.markdown(
        '<div class="cmd-topbar">'
        '<div class="cmd-brand">'
        '<span class="cmd-menu"><span class="cmd-menu-line"></span><span class="cmd-menu-line"></span><span class="cmd-menu-line"></span></span>'
        f'<span>{escape(t(lang, "command_center_title"))}</span>'
        '</div>'
        '<div class="cmd-top-meta">'
        f'<span class="cmd-live">{escape(t(lang, "live_label"))}</span>'
        f'<span>{escape(t(lang, "last_update"))} {escape(update_text)}</span>'
        f'<span class="cmd-select">{escape(t(lang, "shift_label"))}</span>'
        f'<span class="cmd-select">{escape(t(lang, "plant_label"))}</span>'
        f'<span>{escape(date_text)}</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_data_source(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render data-source status in the sidebar."""
    sensor = tables.get("sensor", pd.DataFrame())
    production = tables.get("production", pd.DataFrame())
    models = tables.get("models", pd.DataFrame())
    last_ts = first_available_timestamp(tables, latest=True)
    state, tone, _ = derive_ingestion_state(last_ts, lang)
    agent_count = 0
    if "machine_id" in sensor.columns and not sensor.empty:
        agent_count = int(sensor["machine_id"].nunique())
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### {t(lang, 'data_source_title')}")
    st.sidebar.markdown(status_pill(t(lang, "all_systems_operational") if tone == "ok" else state, tone), unsafe_allow_html=True)
    st.sidebar.caption(f"{t(lang, 'ingestion_api')}: **{t(lang, 'live_label')}**")
    st.sidebar.caption(f"{t(lang, 'database_service')}: **SQLite**")
    st.sidebar.caption(f"{t(lang, 'collector_agents')}: **{agent_count} / {agent_count or 1}**")
    st.sidebar.caption(f"{t(lang, 'model_service')}: **{t(lang, 'model_run_count', value=f'{len(models):,}')}**")
    st.sidebar.caption(f"{t(lang, 'demo_data_note')}: **{t(lang, 'record_count', value=f'{len(sensor) + len(production):,}')}**")
    st.sidebar.button(t(lang, "view_data_pipeline"), use_container_width=True)


def render_line_risk_overview(snapshot: pd.DataFrame, lang: str) -> str:
    """Return the line risk overview panel."""
    if snapshot.empty:
        rows_html = f'<div class="cmd-muted">{escape(t(lang, "machine_matrix_empty"))}</div>'
    else:
        if snapshot["line_id"].nunique() >= 5:
            grouped = (
                snapshot.groupby("line_id", dropna=False)
                .agg(
                    label=("line_id", "first"),
                    avg_condition=("condition_score", "mean"),
                    dominant_signal=("dominant_signal", "first") if "dominant_signal" in snapshot.columns else ("line_id", "first"),
                )
                .reset_index(drop=True)
                .sort_values("avg_condition")
            )
        else:
            machine_source = snapshot.assign(
                label=snapshot["machine_id"].astype(str),
                avg_condition=snapshot["condition_score"],
                dominant_signal=snapshot["dominant_signal"] if "dominant_signal" in snapshot.columns else t(lang, "na"),
            )
            if "line_station" not in machine_source.columns:
                machine_source["line_station"] = machine_source["line_id"].astype(str) if "line_id" in machine_source.columns else machine_source["label"]
            grouped = (
                machine_source
                .sort_values(["condition_score", "derived_anomaly_index"], ascending=[True, False])
                .head(6)[["label", "line_station", "avg_condition", "dominant_signal"]]
            )
        row_parts: list[str] = []
        for rank, (_, row) in enumerate(grouped.iterrows(), start=1):
            risk = round(100.0 - float(row["avg_condition"]), 0)
            label, klass, color = risk_css_from_score(risk, lang)
            decision = t(lang, "decision_machine") if risk >= 40 else t(lang, "decision_monitor")
            owner = t(lang, "owner_maintenance") if risk >= 60 else t(lang, "owner_process_engineering") if risk >= 40 else t(lang, "owner_shift_lead")
            eta = t(lang, "eta_now") if risk >= 80 else t(lang, "eta_this_shift") if risk >= 40 else t(lang, "eta_next_check")
            route = t(lang, "route_machine") if risk >= 40 else t(lang, "route_workflow")
            location = str(row.get("line_station", row.get("label", "")))
            driver = str(row.get("dominant_signal", t(lang, "na")))
            row_parts.append(
                f'<div class="cmd-risk-decision-row {klass}">'
                f'<div class="cmd-risk-rank">{rank:02d}</div>'
                '<div>'
                f'<div class="cmd-risk-title"><span title="{escape(str(row["label"]))}">{escape(str(row["label"])[:18])}</span><span class="cmd-status-{klass}" style="color:{color};">{escape(label)}</span></div>'
                f'<div class="cmd-risk-meta">{escape(location)}<br>{escape(t(lang, "driver"))}: {escape(driver)} | {escape(t(lang, "owner"))}: {escape(owner)} | {escape(t(lang, "eta"))}: {escape(eta)}<br>{escape(t(lang, "decision"))}: {escape(decision)} | {escape(t(lang, "route"))}: {escape(route)}</div>'
                f'<div class="cmd-bar" style="margin-top:.4rem;"><span class="cmd-bar-fill" style="width:{risk:.0f}%;background:{color};"></span></div>'
                '</div>'
                f'<div class="cmd-risk-score" style="color:{color};">{risk:.0f}<small>{escape(t(lang, "risk_units"))}</small></div>'
                '</div>'
            )
        rows_html = '<div class="cmd-risk-decision-list">' + "".join(row_parts) + "</div>"
    return (
        '<div class="cmd-panel">'
        f'<div class="cmd-panel-header"><span class="cmd-panel-title">{escape(t(lang, "line_risk_overview"))}</span>{trust_badge_html(TRUST_DERIVED, lang)}</div>'
        f'<div class="cmd-muted" style="margin:.5rem 0 .65rem;">{escape(t(lang, "risk_score_weighted"))}</div>'
        f'{rows_html}'
        '</div>'
    )


def render_health_matrix_html(snapshot: pd.DataFrame, timeline: pd.DataFrame, lang: str) -> str:
    """Return a machine health matrix panel."""
    row_html: list[str] = []
    if not timeline.empty and "machine_id" in timeline.columns:
        if timeline["line_id"].nunique() >= 5 and "line_id" in timeline.columns:
            group_col = "line_id"
        else:
            group_col = "machine_id"
        source_groups = sorted(timeline[group_col].dropna().unique().tolist())
        for group_id in source_groups[:8]:
            line_df = timeline[timeline[group_col] == group_id].sort_values("timestamp").tail(14)
            values = line_df["condition_score"].tolist() if "condition_score" in line_df.columns else []
            if not values and not snapshot.empty:
                values = snapshot[snapshot[group_col] == group_id]["condition_score"].tolist() if group_col in snapshot.columns else []
            while len(values) < 14:
                values.append(values[-1] if values else 82.0)
            cells = "".join(f'<span class="cmd-cell" title="{float(value):.1f}" style="background:{condition_color(float(value))};"></span>' for value in values[-14:])
            row_html.append(f'<div class="cmd-matrix-label" title="{escape(str(group_id))}">{escape(str(group_id)[:12])}</div><div class="cmd-matrix-cells">{cells}</div>')
    if not row_html:
        row_html.append(f'<div class="cmd-muted">{escape(t(lang, "machine_matrix_empty"))}</div>')
    legend = (
        '<div class="cmd-legend">'
        '<span><i class="cmd-swatch" style="background:#d83a32"></i>0-24</span>'
        '<span><i class="cmd-swatch" style="background:#f0781d"></i>25-44</span>'
        '<span><i class="cmd-swatch" style="background:#f1cf2d"></i>45-61</span>'
        '<span><i class="cmd-swatch" style="background:#6fd346"></i>62-81</span>'
        '<span><i class="cmd-swatch" style="background:#45a236"></i>82-100</span>'
        '</div>'
    )
    return (
        '<div class="cmd-panel">'
        f'<div class="cmd-panel-header"><span class="cmd-panel-title">{escape(t(lang, "machine_health_map"))}</span>{trust_badge_html(TRUST_DERIVED, lang)}</div>'
        f'<div class="cmd-muted" style="margin:.5rem 0 .8rem;">{escape(t(lang, "health_score_label"))}</div>'
        f'<div class="cmd-matrix">{"".join(row_html)}</div>'
        f'{legend}'
        '</div>'
    )


def render_alerts_live_html(alert_rows: list[dict[str, Any]], lang: str) -> str:
    """Return live alerts panel HTML."""
    if not alert_rows:
        alerts_html = f'<div class="cmd-muted">{escape(t(lang, "no_derived_anomaly_records"))}</div>'
    else:
        parts: list[str] = []
        for row in alert_rows:
            severity_label, klass, color = risk_css_from_score(severity_score(row["severity"]), lang)
            parts.append(
                '<div class="cmd-alert">'
                f'<div><span class="cmd-alert-sev cmd-status-{klass}" style="color:{color};">{escape(severity_label)}</span> '
                f'<span class="cmd-muted">{escape(str(row["time"]))}</span></div>'
                f'<div class="cmd-alert-title">{escape(str(row["machine_id"]))} {escape(str(row["title"]))}</div>'
                f'<div class="cmd-alert-meta">{escape(str(row["meta"]))}<br>{escape(t(lang, "derived_anomaly_index"))}: {escape(str(row["score"]))}</div>'
                '</div>'
            )
        alerts_html = "".join(parts)
    return (
        '<div class="cmd-panel">'
        f'<div class="cmd-panel-header"><span class="cmd-panel-title">{escape(t(lang, "alerts_live"))}</span>{trust_badge_html(TRUST_LIVE if alert_rows else TRUST_MODEL_UNAVAILABLE, lang)}</div>'
        f'<div class="cmd-alert-list">{alerts_html}</div>'
        '</div>'
    )


def donut_style(parts: list[tuple[float, str]]) -> str:
    """Return CSS conic-gradient for a donut chart."""
    total = sum(max(0.0, value) for value, _ in parts) or 1.0
    cursor = 0.0
    chunks: list[str] = []
    for value, color in parts:
        sweep = max(0.0, value) / total * 360.0
        chunks.append(f"{color} {cursor:.1f}deg {cursor + sweep:.1f}deg")
        cursor += sweep
    return "conic-gradient(" + ", ".join(chunks) + ")"


def render_event_distribution_html(alert_rows: list[dict[str, Any]], lang: str) -> str:
    """Return event distribution panel."""
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0}
    for row in alert_rows:
        severity = str(row.get("severity", "Medium"))
        if severity not in severity_counts:
            severity = "Medium"
        severity_counts[severity] += 1
    total = sum(severity_counts.values()) or len(alert_rows)
    if total == 0:
        severity_counts = {"Critical": 0, "High": 0, "Medium": 1}
        total = 1
    style = donut_style([(severity_counts["Critical"], "#df3d36"), (severity_counts["High"], "#f0811c"), (severity_counts["Medium"], "#f2cb28")])
    rows = "".join(
        f'<div class="cmd-list-row"><span><i class="cmd-swatch" style="background:{color}"></i>{label}</span><strong>{count}</strong></div>'
        for label, count, color in [
            ("Critical", severity_counts["Critical"], "#df3d36"),
            ("High", severity_counts["High"], "#f0811c"),
            ("Medium", severity_counts["Medium"], "#f2cb28"),
        ]
    )
    return (
        '<div class="cmd-panel compact">'
        f'<div class="cmd-panel-title">{escape(t(lang, "event_distribution_24h"))}</div>'
        '<div class="cmd-donut-wrap" style="margin-top:.85rem;">'
        f'<div class="cmd-donut" style="background:{style};"><div class="cmd-donut-center"><div><small>Total</small>{total}</div></div></div>'
        f'<div>{rows}</div>'
        '</div></div>'
    )


def render_oee_html(production: pd.DataFrame, lang: str) -> str:
    """Return OEE breakdown panel."""
    station_yield = safe_mean(production, "station_yield")
    quality = (station_yield or 0.94) * 100.0
    cycle = safe_mean(production, "cycle_time_sec") or 5.0
    performance = clamp(100.0 - max(0.0, cycle - 4.5) * 4.5, 50.0, 99.0)
    downtime = pd.to_numeric(production.get("downtime_minutes", pd.Series(dtype=float)), errors="coerce").fillna(0).mean() if not production.empty else 0.0
    availability = clamp(100.0 - float(downtime) * 1.8, 50.0, 99.0)
    oee = availability * performance * quality / 10000.0
    style = donut_style([(oee, "#64d246"), (100.0 - oee, "rgba(255,255,255,.09)")])
    rows = "".join(
        f'<div class="cmd-list-row"><span>{label}</span><strong>{value:.1f}%</strong></div>'
        for label, value in [("Availability", availability), ("Performance", performance), ("Quality", quality)]
    )
    return (
        '<div class="cmd-panel compact">'
        f'<div class="cmd-panel-title">{escape(t(lang, "oee_breakdown_24h"))}</div>'
        '<div class="cmd-donut-wrap" style="margin-top:.85rem;">'
        f'<div class="cmd-donut" style="background:{style};"><div class="cmd-donut-center"><div>{oee:.1f}%<small>OEE</small></div></div></div>'
        f'<div>{rows}</div></div></div>'
    )


def render_downtime_html(production: pd.DataFrame, lang: str) -> str:
    """Return top downtime causes panel."""
    if production.empty:
        items = [("No downtime records", 0.0)]
    else:
        source = production.copy()
        source["downtime_minutes"] = pd.to_numeric(source.get("downtime_minutes", 0), errors="coerce").fillna(0)
        group_col = "station_id" if "station_id" in source.columns else "line_id"
        grouped = source.groupby(group_col)["downtime_minutes"].sum().sort_values(ascending=False).head(5)
        items = [(str(index), float(value)) for index, value in grouped.items()]
    max_value = max([value for _, value in items] + [1.0])
    rows = []
    for index, (label, value) in enumerate(items):
        color = ["#df3d36", "#f0811c", "#f2cb28", "#64d246", "#49d8d2"][index % 5]
        rows.append(
            '<div style="margin:.55rem 0;">'
            f'<div class="cmd-list-row"><span>{escape(label)}</span><strong>{value:.0f} min</strong></div>'
            f'<div class="cmd-progress"><span style="width:{value / max_value * 100:.0f}%;background:{color};"></span></div>'
            '</div>'
        )
    return (
        '<div class="cmd-panel compact">'
        f'<div class="cmd-panel-title">{escape(t(lang, "top_downtime_causes"))}</div>'
        f'{"".join(rows)}'
        '</div>'
    )


def render_predictions_summary_html(predictions: pd.DataFrame, timeline: pd.DataFrame, lang: str) -> str:
    """Return predictions summary panel."""
    high_risk = 0
    low_rul = 0
    if not predictions.empty:
        if "failure_probability" in predictions.columns:
            high_risk = int((pd.to_numeric(predictions["failure_probability"], errors="coerce").fillna(0) > .7).sum())
        if "rul_estimate_hours" in predictions.columns:
            low_rul = int((pd.to_numeric(predictions["rul_estimate_hours"], errors="coerce").fillna(999) < 24).sum())
    anomaly_count = int((timeline["derived_anomaly_index"] >= .25).sum()) if not timeline.empty else 0
    rows = [
        ("High failure risk", high_risk, latest_numeric_values(predictions, "failure_probability") or latest_numeric_values(timeline, "derived_anomaly_index"), "#df3d36"),
        ("RUL < 24h", low_rul, latest_numeric_values(predictions, "rul_estimate_hours"), "#f2cb28"),
        ("Anomaly detected", anomaly_count, latest_numeric_values(timeline, "derived_anomaly_index"), "#49d8d2"),
        ("DEMO data records", len(timeline), latest_numeric_values(timeline, "condition_score"), "#64d246"),
    ]
    row_html = "".join(
        '<div class="cmd-list-row">'
        f'<span>{escape(label)}</span><strong>{value}</strong>'
        f'<span class="cmd-small-spark">{sparkline_svg(series, stroke=color)}</span>'
        '</div>'
        for label, value, series, color in rows
    )
    return (
        '<div class="cmd-panel compact">'
        f'<div class="cmd-panel-title">{escape(t(lang, "predictions_summary"))}</div>'
        f'{row_html}'
        '</div>'
    )


def render_data_quality_html(issues: pd.DataFrame, sensor: pd.DataFrame, production: pd.DataFrame, lang: str) -> str:
    """Return data quality panel."""
    total_records = len(sensor) + len(production)
    issue_count = len(issues)
    score = clamp(100.0 - (issue_count / max(1, total_records) * 100.0), 0.0, 100.0)
    style = donut_style([(score, "#64d246"), (100.0 - score, "rgba(255,255,255,.09)")])
    issue_types = issues["issue_type"].value_counts().head(4).to_dict() if not issues.empty and "issue_type" in issues.columns else {}
    if not issue_types:
        issue_types = {"Missing values": 0, "Outliers": 0, "Duplicates": 0, "Gaps": 0}
    rows = "".join(f'<div class="cmd-list-row"><span>{escape(str(key))}</span><strong>{value}</strong></div>' for key, value in issue_types.items())
    return (
        '<div class="cmd-panel compact">'
        f'<div class="cmd-panel-title">{escape(t(lang, "data_quality_24h"))}</div>'
        '<div class="cmd-donut-wrap" style="margin-top:.85rem;">'
        f'<div class="cmd-donut" style="background:{style};"><div class="cmd-donut-center"><div>{score:.1f}%<small>Score</small></div></div></div>'
        f'<div>{rows}</div></div></div>'
    )


def render_machine_inspector_command(
    snapshot: pd.DataFrame,
    sensor: pd.DataFrame,
    production: pd.DataFrame,
    predictions: pd.DataFrame,
    alert_rows: list[dict[str, Any]],
    lang: str,
) -> None:
    """Render the command-center right-side machine inspector."""
    if snapshot.empty:
        st.markdown(
            '<div class="cmd-inspector">'
            f'<div class="cmd-inspector-title">{escape(t(lang, "machine_inspector_title"))}</div>'
            f'<div class="cmd-muted">{escape(t(lang, "machine_matrix_empty"))}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return
    ordered = snapshot.sort_values(["condition_score", "derived_anomaly_index"], ascending=[True, False])
    machines = ordered["machine_id"].astype(str).tolist()
    selected_machine = st.selectbox(
        t(lang, "select_machine_for_deep_dive"),
        machines,
        key="cmd_machine_inspector_select",
        label_visibility="collapsed",
    )
    row = snapshot[snapshot["machine_id"].astype(str) == selected_machine].iloc[0]
    selected_sensor = sensor[sensor["machine_id"].astype(str) == selected_machine].sort_values("timestamp") if not sensor.empty and "machine_id" in sensor.columns else pd.DataFrame()
    latest_sensor = selected_sensor.tail(1).iloc[0] if not selected_sensor.empty else pd.Series(dtype=object)
    selected_production = pd.DataFrame()
    if not production.empty and {"line_id", "station_id"} <= set(production.columns):
        selected_production = production[
            (production["line_id"].astype(str) == str(row.get("line_id", "")))
            & (production["station_id"].astype(str) == str(row.get("station_id", "")))
        ].sort_values("timestamp")
    selected_predictions = predictions[predictions["machine_id"].astype(str) == selected_machine].sort_values("timestamp") if not predictions.empty and "machine_id" in predictions.columns else pd.DataFrame()
    latest_prediction = selected_predictions.tail(1).iloc[0] if not selected_predictions.empty else pd.Series(dtype=object)
    failure_probability = sensor_value(latest_prediction, "failure_probability")
    if failure_probability is None:
        failure_probability = float(row.get("derived_anomaly_index", 0.0))
    rul = sensor_value(latest_prediction, "rul_estimate_hours")
    if rul is None:
        rul = max(1.0, (float(row.get("condition_score", 0.0)) / 100.0) * 24.0)
    temp = sensor_value(latest_sensor, "process_temperature")
    condition = float(row.get("condition_score", 0.0))
    risk_label = str(row.get("risk_level", ""))
    risk_tone = str(row.get("risk_tone", "ok"))
    chip_class = "critical" if risk_tone == "risk" else "warning" if risk_tone == "warn" else "stable"
    health_color = condition_color(condition)
    failure_color = "#ff5148" if failure_probability >= .65 else "#f4ce31" if failure_probability >= .35 else "#67e34a"
    health_arc = clamp(condition, 0.0, 100.0) * 3.6
    failure_arc = clamp(failure_probability, 0.0, 1.0) * 360.0
    telemetry = [
        ("Vibration RMS", "vibration_rms", "mm/s", "#ff5148" if condition < 62 else "#49d8d2"),
        ("Motor Current", "motor_current", "A", "#49d8d2"),
        ("Torque", "torque", "Nm", "#49d8d2"),
        ("Temperature", "process_temperature", "C", "#ff5148" if (temp or 0) > 70 else "#49d8d2"),
        ("Tool Wear", "tool_wear", "%", "#f2cb28"),
    ]
    telemetry_rows = []
    for label, column, unit, color in telemetry:
        value = sensor_value(latest_sensor, column)
        delta = baseline_delta_text(selected_sensor, column, value, lang, suffix=f" {unit.strip()}" if unit.strip() else "")
        telemetry_rows.append(
            '<div class="cmd-telemetry-row">'
            f'<span>{escape(label)}</span>'
            f'<strong class="cmd-telemetry-value">{escape(format_metric(value, unit, decimals=2, lang=lang))}<small>{escape(delta)}</small></strong>'
            f'<span class="cmd-small-spark">{sparkline_svg(latest_numeric_values(selected_sensor, column), stroke=color)}</span>'
            '</div>'
        )
    lineage_rows = [
        (t(lang, "last_record"), format_timestamp_short(row.get("timestamp"), lang)),
        (t(lang, "sensor_rows_label"), f"{len(selected_sensor):,}"),
        (t(lang, "production_rows_label"), f"{len(selected_production):,}"),
        (t(lang, "model_rows_label"), f"{len(selected_predictions):,}"),
        (t(lang, "source_label"), str(row.get("source", t(lang, "na")))),
    ]
    lineage_html = (
        f'<div class="cmd-lineage"><div class="cmd-label">{escape(t(lang, "data_lineage"))}</div>'
        + "".join(
            f'<div class="cmd-lineage-row"><span>{escape(label)}</span><strong title="{escape(value)}">{escape(value)}</strong></div>'
            for label, value in lineage_rows
        )
        + "</div>"
    )
    driver_html = (
        f'<div class="cmd-lineage"><div class="cmd-label">{escape(t(lang, "signal_drivers"))}</div>'
        + "".join(
            '<div class="cmd-driver-row">'
            f'<div class="cmd-driver-meta"><span>{escape(label)}</span><strong>{score:.0f}%</strong></div>'
            f'<div class="cmd-driver-bar" title="{escape(value_text)}"><span style="width:{score:.0f}%;background:{driver_color(score)};"></span></div>'
            '</div>'
            for label, score, value_text in signal_driver_scores(latest_sensor, lang)[:5]
        )
        + "</div>"
    )
    basis_html = (
        f'<div class="cmd-lineage"><div class="cmd-label">{escape(t(lang, "calculation_basis"))}</div>'
        f'<div class="cmd-alert-meta">{escape(t(lang, "calculation_basis_body"))}</div></div>'
    )
    latest_alert = next((item for item in alert_rows if str(item.get("machine_id")) == selected_machine), alert_rows[0] if alert_rows else None)
    alert_html = ""
    if latest_alert:
        alert_html = (
            '<div class="cmd-telemetry">'
            f'<div class="cmd-label">{escape(t(lang, "latest_anomaly"))}</div>'
            f'<div class="cmd-alert-title">{escape(str(latest_alert["title"]))}</div>'
            f'<div class="cmd-alert-meta">{escape(str(latest_alert["time"]))}<br>{escape(t(lang, "derived_anomaly_index"))}: {escape(str(latest_alert["score"]))}</div>'
            '</div>'
        )
    st.markdown(
        '<div class="cmd-inspector">'
        f'<div class="cmd-inspector-title">{escape(t(lang, "machine_inspector_title"))}</div>'
        f'<div class="cmd-machine-name">{escape(selected_machine)}</div><span class="cmd-chip {chip_class}">{escape(risk_label)}</span>'
        f'<div class="cmd-alert-meta">{escape(t(lang, "line_label"))} {escape(str(row.get("line_id", "")))} / {escape(t(lang, "station_label"))} {escape(str(row.get("station_id", "")))}</div>'
        f'<div class="cmd-tabs"><span>{escape(t(lang, "detail_tab_overview"))}</span><span>{escape(t(lang, "detail_tab_signals"))}</span><span>{escape(t(lang, "detail_tab_context"))}</span><span>{escape(t(lang, "detail_tab_events"))}</span></div>'
        '<div class="cmd-gauge-grid">'
        f'<div class="cmd-ring-card"><div class="cmd-label">{escape(t(lang, "health_score_label"))}</div><div class="cmd-ring" style="background:conic-gradient({health_color} 0deg {health_arc:.1f}deg, rgba(255,255,255,.08) {health_arc:.1f}deg 360deg);"><div class="cmd-ring-value"><div>{condition:.0f}<small>/100</small></div></div></div></div>'
        f'<div class="cmd-ring-card"><div class="cmd-label">{escape(t(lang, "failure_probability_label"))}</div><div class="cmd-ring" style="background:conic-gradient({failure_color} 0deg {failure_arc:.1f}deg, rgba(255,255,255,.08) {failure_arc:.1f}deg 360deg);"><div class="cmd-ring-value"><div>{failure_probability:.2f}<small>{escape(risk_label)}</small></div></div></div></div>'
        f'<div class="cmd-mini danger"><div class="cmd-label">{escape(t(lang, "rul_estimate_label"))}</div><div class="cmd-mini-value">{rul:.1f}</div><div class="cmd-muted">hours</div></div>'
        f'<div class="cmd-mini"><div class="cmd-label">{escape(t(lang, "temp_label"))}</div><div class="cmd-mini-value">{format_metric(temp, " C", decimals=1, lang=lang)}</div><div class="cmd-muted">{escape(t(lang, "latest_event"))}</div></div>'
        '</div>'
        f'{lineage_html}'
        f'{driver_html}'
        f'<div class="cmd-telemetry"><div class="cmd-label">{escape(t(lang, "key_telemetry_live"))}</div>{"".join(telemetry_rows)}</div>'
        f'{basis_html}'
        f'{alert_html}'
        '<div class="cmd-actions">'
        f'<span class="cmd-action-tile"><strong>{escape(t(lang, "event_trail_ready"))}</strong>{len(selected_sensor):,} {escape(t(lang, "recent_machine_records"))}</span>'
        f'<span class="cmd-action-tile"><strong>{escape(t(lang, "maintenance_handoff"))}</strong>{escape(t(lang, "writeback_not_connected"))}</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


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


def format_age(ts: pd.Timestamp | None, lang: str = DEFAULT_LANGUAGE) -> str:
    """Return a human-friendly age for a UTC timestamp."""
    if ts is None or pd.isna(ts):
        return t(lang, "na")
    try:
        delta = pd.Timestamp.now(tz="UTC") - pd.Timestamp(ts)
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return t(lang, "age_seconds", value=seconds)
        minutes = seconds // 60
        if minutes < 60:
            return t(lang, "age_minutes", value=minutes)
        hours = minutes // 60
        if hours < 48:
            return t(lang, "age_hours", value=hours)
        days = hours // 24
        return t(lang, "age_days", value=days)
    except Exception:
        return t(lang, "na")


def derive_ingestion_state(last_ts: pd.Timestamp | None, lang: str = DEFAULT_LANGUAGE) -> tuple[str, str, str]:
    """Return display label, tone, and explanation for current ingestion freshness."""
    if last_ts is None:
        return t(lang, "waiting_for_data"), "warn", t(lang, "waiting_for_data_note")
    try:
        age_seconds = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(last_ts)).total_seconds()
    except Exception:
        return t(lang, "timestamp_unavailable"), "warn", t(lang, "timestamp_unavailable_note")
    if age_seconds < 120:
        return t(lang, "live_stream_active"), "ok", t(lang, "live_stream_active_note")
    if age_seconds < 3600:
        return t(lang, "stream_delayed"), "warn", t(lang, "stream_delayed_note")
    return t(lang, "replay_offline"), "info", t(lang, "replay_offline_note")


def build_action_queue(
    latest_predictions: pd.DataFrame,
    alerts: pd.DataFrame,
    issues: pd.DataFrame,
    max_items: int = 8,
    lang: str = DEFAULT_LANGUAGE,
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
                        "area": f"{row.get('line_id', t(lang, 'na'))} / {row.get('station_id', t(lang, 'na'))}",
                        "asset": row.get("machine_id", t(lang, "na")),
                        "signal": t(lang, "risk_signal", risk=risk.upper(), health=format_metric(row.get("health_score"), lang=lang)),
                        "suggested_action": row.get("recommended_action") or t(lang, "inspect_asset"),
                        "decision": t(lang, "decision_machine"),
                        "owner": t(lang, "owner_maintenance"),
                        "eta": t(lang, "eta_now") if risk == "critical" else t(lang, "eta_this_shift"),
                        "route": t(lang, "route_machine"),
                        "trust_level": TRUST_LIVE,
                    }
                )

    if not alerts.empty:
        for _, row in alerts.head(max_items).iterrows():
            severity = str(row.get("severity", "")).lower()
            rows.append(
                {
                    "priority": "P1" if severity == "critical" else "P2",
                    "area": f"{row.get('line_id', t(lang, 'na'))} / {row.get('station_id', t(lang, 'na'))}",
                    "asset": row.get("machine_id", t(lang, "na")),
                    "signal": t(lang, "anomaly_alert_signal", score=row.get("anomaly_score", t(lang, "na"))),
                    "suggested_action": row.get("message") or t(lang, "review_trend"),
                    "decision": t(lang, "decision_anomaly"),
                    "owner": t(lang, "owner_shift_lead"),
                    "eta": t(lang, "eta_now") if severity == "critical" else t(lang, "eta_this_shift"),
                    "route": t(lang, "route_anomaly"),
                    "trust_level": TRUST_LIVE,
                }
            )

    if not issues.empty:
        severe = issues[issues.get("severity", pd.Series(dtype=str)).astype(str).str.lower().isin(["high", "critical"])] if "severity" in issues.columns else pd.DataFrame()
        source = severe if not severe.empty else issues.head(3)
        for _, row in source.head(3).iterrows():
            rows.append(
                {
                    "priority": "P3",
                    "area": f"{row.get('line_id', t(lang, 'na'))} / {row.get('station_id', t(lang, 'na'))}",
                    "asset": row.get("machine_id", row.get("entity_id", t(lang, "na"))),
                    "signal": t(lang, "data_quality_signal", issue=row.get("issue_type", t(lang, "na"))),
                    "suggested_action": t(lang, "verify_channel"),
                    "decision": t(lang, "decision_quality"),
                    "owner": t(lang, "owner_data_engineering"),
                    "eta": t(lang, "eta_today"),
                    "route": t(lang, "route_quality"),
                    "trust_level": TRUST_NOT_CHECKED,
                }
            )

    if not rows:
        return pd.DataFrame(
            [
                {
                    "priority": "Monitor",
                    "area": t(lang, "all_lines"),
                    "asset": t(lang, "system"),
                    "signal": t(lang, "no_high_priority_action"),
                    "suggested_action": t(lang, "continue_collecting"),
                    "decision": t(lang, "decision_monitor"),
                    "owner": t(lang, "owner_shift_lead"),
                    "eta": t(lang, "eta_next_check"),
                    "route": t(lang, "route_workflow"),
                    "trust_level": TRUST_MODEL_UNAVAILABLE,
                }
            ]
        )
    priority_order = {"P1": 0, "P2": 1, "P3": 2, "Monitor": 3}
    out = pd.DataFrame(rows).drop_duplicates()
    out["_order"] = out["priority"].map(priority_order).fillna(9)
    return out.sort_values(["_order", "area"]).drop(columns=["_order"]).head(max_items)


def render_action_queue_html(action_queue: pd.DataFrame, lang: str) -> str:
    """Return a compact action queue panel for the command center."""
    rows: list[str] = []
    for _, row in action_queue.head(5).iterrows():
        priority = str(row.get("priority", "Monitor"))
        tone = "risk" if priority == "P1" else "warn" if priority in {"P2", "P3"} else ""
        priority_label = t(lang, "monitor") if priority == "Monitor" else priority
        trust_level = str(row.get("trust_level", TRUST_DERIVED))
        rows.append(
            f'<div class="cmd-action-row {tone}">'
            f'<div><span class="cmd-priority-badge">{escape(priority_label)}</span><div class="cmd-action-sub" style="margin-top:.35rem;">{escape(str(row.get("area", "")))}</div></div>'
            f'<div><div class="cmd-action-main">{escape(str(row.get("asset", "")))}</div><div class="cmd-action-sub">{escape(str(row.get("signal", "")))}</div>'
            f'<div class="cmd-action-meta"><span>{escape(t(lang, "owner"))}: {escape(str(row.get("owner", "")))}</span><span>{escape(t(lang, "eta"))}: {escape(str(row.get("eta", "")))}</span></div></div>'
            f'<div><div class="cmd-action-decision">{escape(str(row.get("decision", row.get("suggested_action", ""))))}</div>'
            f'<div class="cmd-action-sub">{escape(t(lang, "route"))}: {escape(str(row.get("route", "")))}</div>{trust_badge_html(trust_level, lang)}</div>'
            '</div>'
        )
    return (
        '<div class="cmd-panel">'
        f'<div class="cmd-panel-header"><span class="cmd-panel-title">{escape(t(lang, "action_queue_title"))}</span>{trust_badges_html([TRUST_LIVE, TRUST_DERIVED, TRUST_MODEL_UNAVAILABLE, TRUST_NOT_CHECKED], lang)}</div>'
        f'<div class="cmd-muted">{escape(t(lang, "action_queue_caption"))}</div>'
        f'<div class="cmd-action-list">{"".join(rows)}</div>'
        '</div>'
    )


def render_ops_context(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render the operational context strip below the main header."""
    sensor = tables.get("sensor", pd.DataFrame())
    production = tables.get("production", pd.DataFrame())
    models = tables.get("models", pd.DataFrame())
    predictions = tables.get("predictions", pd.DataFrame())
    alerts = tables.get("alerts", pd.DataFrame())

    first_ts = first_available_timestamp(tables, latest=False)
    last_ts = first_available_timestamp(tables, latest=True)
    state, tone, explanation = derive_ingestion_state(last_ts, lang)
    trained_models = models["model_name"].nunique() if not models.empty and "model_name" in models.columns else len(models)
    high_alerts = 0
    if not alerts.empty and "severity" in alerts.columns:
        high_alerts = int(alerts["severity"].astype(str).str.lower().isin(["high", "critical"]).sum())
    if high_alerts == 0 and not predictions.empty and "risk_level" in predictions.columns:
        high_alerts = int(predictions["risk_level"].astype(str).str.lower().isin(["high", "critical"]).sum())

    render_status_pills(
        [
            (state, tone),
            (t(lang, "mode_name"), "info"),
            (t(lang, "sensor_events", value=f"{len(sensor):,}"), "info"),
            (t(lang, "production_events", value=f"{len(production):,}"), "info"),
            (t(lang, "model_runs_pill", value=trained_models), "ok" if trained_models else "warn"),
        ]
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_card(t(lang, "data_freshness"), format_age(last_ts, lang), explanation)
    with c2:
        span = t(lang, "na") if first_ts is None or last_ts is None else t(lang, "date_range", start=first_ts.date(), end=last_ts.date())
        render_card(t(lang, "data_window"), span, t(lang, "data_window_caption"))
    with c3:
        render_card(t(lang, "risk_posture"), t(lang, "high_signals", value=high_alerts), t(lang, "risk_caption"))
    with c4:
        render_card(t(lang, "database"), get_db_path().name, t(lang, "database_caption"))


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
def read_table(
    table_name: str,
    order_by: str | None = None,
    limit: int | None = None,
    lang: str = DEFAULT_LANGUAGE,
) -> pd.DataFrame:
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
        st.warning(t(lang, "table_read_failed", table=table_name, error=exc))
        return pd.DataFrame()


@st.cache_data(ttl=5)
def read_query(query: str, params: tuple[Any, ...] = (), lang: str = DEFAULT_LANGUAGE) -> pd.DataFrame:
    """Read a custom SQL query safely."""
    try:
        with connect_db() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return normalize_timestamps(df)
    except Exception as exc:
        st.warning(t(lang, "query_failed", error=exc))
        return pd.DataFrame()


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Convert common timestamp columns to pandas datetime."""
    out = df.copy()
    for col in ["timestamp", "created_at", "updated_at", "detected_at", "started_at", "completed_at", "event_timestamp", "sensor_timestamp", "first_seen_at", "last_seen_at", "due_at"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce", utc=True)
    return out


def show_empty(message: str, command: str | None = None) -> None:
    """Show a consistent empty-state message."""
    st.info(message)
    if command:
        st.code(command, language="bash")


def plot_line(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    color: str | None = None,
    title: str = "",
    lang: str = DEFAULT_LANGUAGE,
    time_window_hours: int | None = 24,
    max_points: int = 900,
    thresholds: list[tuple[float, str, str]] | None = None,
) -> None:
    """Render a line chart with Plotly when available, otherwise Streamlit line chart."""
    if df.empty or x not in df.columns:
        show_empty(t(lang, "empty_chart"))
        return

    try:
        chart_df = prepare_timeseries(df, timestamp_col=x, group_col=color, hours=time_window_hours, max_points=max_points)
        if px is not None:
            fig = px.line(chart_df, x=x, y=y, color=color, title=title, markers=False, render_mode="svg")
            fig.update_layout(
                height=390,
                template="plotly_dark",
                hovermode="x unified",
                legend_title_text="",
                showlegend=len(fig.data) > 1,
                legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10, r=10, t=58, b=10),
                font=dict(size=12, color="#eaf4e9"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(6,10,12,.72)",
                xaxis=dict(gridcolor="rgba(255,255,255,.08)"),
                yaxis=dict(gridcolor="rgba(255,255,255,.08)"),
            )
            fig.update_traces(line=dict(width=1.85))
            for threshold, label, color_value in thresholds or []:
                fig.add_hline(
                    y=threshold,
                    line_dash="dash",
                    line_width=1,
                    line_color=color_value,
                    annotation_text=label,
                    annotation_position="top left",
                    annotation_font_size=10,
                )
            st.plotly_chart(fig, width="stretch")
            st.caption(t(lang, "chart_points_caption"))
        else:
            cols = [y] if isinstance(y, str) else y
            st.line_chart(chart_df.set_index(x)[cols])
    except Exception as exc:
        st.warning(t(lang, "chart_failed", error=exc))


def plot_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str = "",
    lang: str = DEFAULT_LANGUAGE,
) -> None:
    """Render a bar chart with fallback."""
    if df.empty or x not in df.columns or y not in df.columns:
        show_empty(t(lang, "empty_chart"))
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
            st.plotly_chart(fig, width="stretch")
        else:
            st.bar_chart(df.set_index(x)[y])
    except Exception as exc:
        st.warning(t(lang, "chart_failed", error=exc))


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


def format_metric(value: Any, suffix: str = "", decimals: int = 2, lang: str = DEFAULT_LANGUAGE) -> str:
    """Format metric value for display."""
    if value is None:
        return t(lang, "na")
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
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """Build a lightweight Markdown operational report."""
    latest_prediction = latest_by_group(predictions, ["machine_id"], "timestamp")
    avg_health = safe_mean(latest_prediction, "health_score")
    avg_rul = safe_mean(latest_prediction, "rul_estimate_hours")
    anomaly_count = len(alerts) if not alerts.empty else int(pd.to_numeric(predictions.get("anomaly_flag", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not predictions.empty else 0
    if anomaly_count == 0:
        derived_timeline = build_condition_timeline(sensor, limit=1000)
        if not derived_timeline.empty and "derived_anomaly_index" in derived_timeline.columns:
            anomaly_count = int((derived_timeline["derived_anomaly_index"] >= 0.5).sum())

    generated_at = datetime.now(timezone.utc).isoformat()
    last_prediction_time = None
    if not predictions.empty and "timestamp" in predictions.columns:
        parsed_ts = pd.to_datetime(predictions["timestamp"], errors="coerce", utc=True).dropna()
        last_prediction_time = parsed_ts.max().isoformat() if not parsed_ts.empty else None

    action_queue = build_action_queue(latest_prediction, alerts, issues, max_items=5, lang=lang)
    action_lines = "\n".join(
        f"- **{row['priority']}** | {row['area']} | {row['asset']} | {row['signal']} - {row['suggested_action']}"
        for _, row in action_queue.iterrows()
    )

    return f"""# {t(lang, "report_title")}

{t(lang, "generated_at")}: `{generated_at}`

## {t(lang, "data_policy")}

{t(lang, "disclaimer")}

## {t(lang, "shift_summary")}

- {t(lang, "report_sensor_readings")}: **{len(sensor)}**
- {t(lang, "report_production_events")}: **{len(production)}**
- {t(lang, "report_predictions")}: **{len(predictions)}**
- {t(lang, "report_anomaly_alerts")}: **{len(alerts)}**
- {t(lang, "report_quality_issues")}: **{len(issues)}**
- {t(lang, "report_model_runs")}: **{len(model_runs)}**
- {t(lang, "report_avg_health")}: **{format_metric(avg_health, lang=lang)}**
- {t(lang, "report_avg_rul")}: **{format_metric(avg_rul, lang=lang)}**
- {t(lang, "report_anomaly_count")}: **{anomaly_count}**
- {t(lang, "report_latest_prediction")}: **{last_prediction_time or t(lang, 'na')}**

## {t(lang, "operator_queue")}

{action_lines}

## {t(lang, "operating_rhythm")}

1. {t(lang, "rhythm_1")}
2. {t(lang, "rhythm_2")}
3. {t(lang, "rhythm_3")}
4. {t(lang, "rhythm_4")}
5. {t(lang, "rhythm_5")}
"""


def download_dataframe(df: pd.DataFrame, file_name: str, label: str, lang: str) -> None:
    """Render a CSV download button for a DataFrame."""
    if df.empty:
        st.caption(t(lang, "no_data_for_label", label=label))
        return
    st.download_button(
        label=t(lang, "download_csv", label=label),
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=file_name,
        mime="text/csv",
    )


def render_header() -> str:
    """Render dashboard header and sidebar."""
    initial_lang = st.session_state.get("smop_language", DEFAULT_LANGUAGE)
    st.set_page_config(page_title=t(initial_lang, "app_title"), layout="wide")
    inject_global_style()
    lang = st.sidebar.selectbox(
        "Language / ภาษา / 中文 / 日本語",
        list(LANGUAGE_OPTIONS),
        index=language_index(),
        format_func=lambda code: LANGUAGE_OPTIONS[code],
        key="smop_language",
    )
    st.sidebar.markdown(f"## {t(lang, 'command_center_title')}")
    st.sidebar.caption(f"{t(lang, 'site')}: **{t(lang, 'site_name')}**")
    st.sidebar.caption(f"{t(lang, 'area')}: **{t(lang, 'area_name')}**")
    st.sidebar.caption(f"{t(lang, 'sqlite')}: **{get_db_path().name}**")
    if st.sidebar.button(t(lang, "refresh_data")):
        st.cache_data.clear()
        st.rerun()
    return lang


def sync_workflow_cases(lang: str, limit: int = 50) -> dict[str, Any]:
    """Sync local workflow cases from the current SQLite signals."""
    if operations_repository is None:
        return {"created": 0, "updated": 0, "open_cases": 0, "signals_seen": 0}
    try:
        return operations_repository.sync_operational_cases_from_signals(get_db_path(), limit=limit)
    except Exception as exc:
        st.warning(t(lang, "query_failed", error=exc))
        return {"created": 0, "updated": 0, "open_cases": 0, "signals_seen": 0}


def load_all_tables(lang: str) -> dict[str, pd.DataFrame]:
    """Load all dashboard-relevant tables."""
    if operations_repository is not None:
        try:
            operations_repository.initialize_database(get_db_path())
            operations_repository.sync_operational_cases_from_signals(get_db_path(), limit=40)
        except Exception as exc:
            st.warning(t(lang, "query_failed", error=exc))
    return {
        "sensor": read_table("sensor_readings", order_by="timestamp", lang=lang),
        "production": read_table("production_events", order_by="timestamp", lang=lang),
        "issues": read_table("data_quality_issues", order_by="detected_at DESC", lang=lang),
        "logs": read_table("data_acquisition_logs", order_by="created_at DESC", lang=lang),
        "models": read_table("model_training_runs", order_by="id DESC", lang=lang),
        "predictions": read_table("predictions", order_by="id DESC", lang=lang),
        "alerts": read_table("anomaly_alerts", order_by="id DESC", lang=lang),
        "hints": read_table("diagnostic_hints", order_by="id DESC", lang=lang),
        "cases": read_table("operational_cases", order_by="updated_at DESC", lang=lang),
        "case_events": read_table("operational_case_events", order_by="id DESC", lang=lang),
        "work_orders": read_table("work_orders", order_by="updated_at DESC", lang=lang),
        "users": read_table("app_users", order_by="user_id", lang=lang),
        "case_owners": read_table("case_ownership", order_by="assigned_at DESC", lang=lang),
        "approvals": read_table("case_approvals", order_by="requested_at DESC", lang=lang),
        "notifications": read_table("notifications", order_by="created_at DESC", lang=lang),
        "outbox": read_table("integration_outbox", order_by="updated_at DESC", lang=lang),
    }


def page_executive_overview(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render the command-center page."""
    sensor = tables["sensor"]
    production = tables["production"]
    predictions = tables["predictions"]
    alerts = tables["alerts"]
    issues = tables["issues"]
    snapshot = build_machine_snapshot(sensor, production, predictions, lang)
    condition_timeline = build_condition_timeline(sensor, limit=520)
    alert_rows = build_command_alerts(alerts, condition_timeline, lang)

    latest_predictions = latest_by_group(predictions, ["machine_id"], "timestamp")
    total_machines = sensor["machine_id"].nunique() if "machine_id" in sensor.columns and not sensor.empty else 0
    total_lines = pd.concat(
        [
            sensor[["line_id"]] if "line_id" in sensor.columns else pd.DataFrame(columns=["line_id"]),
            production[["line_id"]] if "line_id" in production.columns else pd.DataFrame(columns=["line_id"]),
        ],
        ignore_index=True,
    )["line_id"].nunique()
    active_lines = 0
    last_ts = first_available_timestamp(tables, latest=True)
    if last_ts is not None and not production.empty and "timestamp" in production.columns and "line_id" in production.columns:
        window = pd.Timestamp(last_ts) - pd.Timedelta(minutes=5)
        active_lines = int(production[production["timestamp"] >= window]["line_id"].nunique())
    active_lines = active_lines or total_lines

    critical_machines = 0
    warning_machines = 0
    if not latest_predictions.empty and "risk_level" in latest_predictions.columns:
        critical_machines = int(latest_predictions["risk_level"].isin(["high", "critical"]).sum())
        warning_machines = int(latest_predictions["risk_level"].isin(["medium", "warning"]).sum())
    elif not snapshot.empty and "risk_tone" in snapshot.columns:
        critical_machines = int(snapshot["risk_tone"].astype(str).eq("risk").sum())
        warning_machines = int(snapshot["risk_tone"].astype(str).eq("warn").sum())

    anomaly_count = len(alerts) if not alerts.empty else int(pd.to_numeric(predictions.get("anomaly_flag", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not predictions.empty else 0
    if anomaly_count == 0 and not condition_timeline.empty:
        anomaly_count = int((condition_timeline["derived_anomaly_index"] >= 0.25).sum())
    station_yield = safe_mean(production, "station_yield")
    downtime_mean = pd.to_numeric(production.get("downtime_minutes", pd.Series(dtype=float)), errors="coerce").fillna(0).mean() if not production.empty else 0.0
    cycle_mean = safe_mean(production, "cycle_time_sec") or 5.0
    availability = clamp(100.0 - float(downtime_mean) * 1.8, 50.0, 99.0)
    performance = clamp(100.0 - max(0.0, cycle_mean - 4.5) * 4.5, 50.0, 99.0)
    quality = (station_yield or 0.94) * 100.0
    oee = availability * performance * quality / 10000.0
    state_label, state_tone, state_note = derive_ingestion_state(last_ts, lang)
    freshness_trust = TRUST_LIVE if state_tone == "ok" else TRUST_REPLAY
    risk_trust = TRUST_LIVE if not predictions.empty or not alerts.empty else TRUST_DERIVED
    model_trust = TRUST_LIVE if not predictions.empty else TRUST_MODEL_UNAVAILABLE
    quality_trust = TRUST_LIVE if not issues.empty else TRUST_NOT_CHECKED
    action_queue = build_action_queue(latest_predictions, alerts, issues, max_items=5, lang=lang)
    open_actions = int((action_queue["priority"].astype(str) != "Monitor").sum()) if "priority" in action_queue.columns else 0
    model_value = f"{len(predictions):,}" if not predictions.empty else trust_label(TRUST_MODEL_UNAVAILABLE, lang)
    quality_value = f"{len(issues):,}" if not issues.empty else trust_label(TRUST_NOT_CHECKED, lang)

    kpi_html = "".join(
        [
            command_metric_card(
                t(lang, "data_freshness"),
                format_age(last_ts, lang),
                state_label,
                latest_numeric_values(production, "throughput_count"),
                "ok",
                [freshness_trust],
                lang,
            ),
            command_metric_card(
                t(lang, "risk_posture"),
                t(lang, "high_signals", value=critical_machines + warning_machines + anomaly_count),
                f"{len(alert_rows)} {t(lang, 'alerts_live')}",
                latest_numeric_values(condition_timeline, "derived_anomaly_index"),
                "risk" if anomaly_count or critical_machines else "info",
                [risk_trust],
                lang,
            ),
            command_metric_card(
                t(lang, "open_action_count"),
                str(open_actions),
                t(lang, "drilldown_hint"),
                latest_numeric_values(snapshot, "condition_score"),
                "warn" if open_actions else "ok",
                [TRUST_LIVE if open_actions else TRUST_DERIVED, model_trust],
                lang,
            ),
            command_metric_card(
                t(lang, "model_readiness"),
                model_value,
                f"{t(lang, 'data_quality_gate')}: {quality_value}",
                latest_numeric_values(predictions, "failure_probability"),
                "info" if not predictions.empty else "warn",
                [model_trust, quality_trust],
                lang,
            ),
        ]
    )

    st.markdown(f'<div class="cmd-kpi-grid">{kpi_html}</div>', unsafe_allow_html=True)
    st.caption(f"{t(lang, 'metric_trust')}: {trust_label(TRUST_LIVE, lang)} / {trust_label(TRUST_REPLAY, lang)} / {trust_label(TRUST_DERIVED, lang)} / {trust_label(TRUST_MODEL_UNAVAILABLE, lang)} / {trust_label(TRUST_NOT_CHECKED, lang)}")
    st.markdown(
        '<div class="cmd-decision-grid">'
        f'{render_action_queue_html(action_queue, lang)}'
        f'{render_line_risk_overview(snapshot, lang)}'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="cmd-panels-2">'
        f'{render_health_matrix_html(snapshot, condition_timeline, lang)}'
        f'{render_alerts_live_html(alert_rows, lang)}'
        '</div>',
        unsafe_allow_html=True,
    )
    st.info(t(lang, "drilldown_hint"))


WORKFLOW_STATUS_ORDER = ["new", "triage", "assigned", "investigating", "mitigated", "resolved"]


def workflow_status_label(status: str, lang: str) -> str:
    """Return localized workflow status label."""
    return t(lang, f"{status}_status") if f"{status}_status" in TEXT[DEFAULT_LANGUAGE] else status.title()


def workflow_metric_card(title: str, value: str, sub: str = "", tone: str = "ok", trust_level: str = TRUST_LIVE, lang: str = DEFAULT_LANGUAGE) -> str:
    """Return a workflow metric card."""
    return command_metric_card(title, value, sub, [0.18, 0.24, 0.2, 0.33, 0.28], tone, [trust_level], lang)


def render_workflow_board_html(cases: pd.DataFrame, lang: str, max_per_lane: int = 4) -> str:
    """Return workflow kanban board HTML from case records."""
    if cases.empty:
        return (
            '<div class="cmd-panel">'
            f'<div class="cmd-muted">{escape(t(lang, "no_workflow_cases"))}</div>'
            '</div>'
        )
    lanes: list[str] = []
    for status in WORKFLOW_STATUS_ORDER:
        lane_df = cases[cases["status"].astype(str).str.lower() == status].copy() if "status" in cases.columns else pd.DataFrame()
        cards: list[str] = []
        for _, row in lane_df.head(max_per_lane).iterrows():
            severity = str(row.get("severity", "medium")).lower()
            machine = str(row.get("machine_id") or row.get("station_id") or row.get("line_id") or "")
            due = row.get("due_at")
            due_text = format_timestamp_short(due, lang) if due is not None and not pd.isna(due) else t(lang, "na")
            owner = str(row.get("owner") or "unassigned")
            cards.append(
                f'<div class="cmd-case-card {escape(severity)}">'
                f'<div class="cmd-case-title">{escape(str(row.get("title", "")))}</div>'
                f'<span class="cmd-case-chip {escape(severity)}">{escape(severity)}</span>'
                f'<div class="cmd-case-meta">{escape(machine)}<br>{escape(t(lang, "owner"))}: {escape(owner)}<br>{escape(t(lang, "due_at"))}: {escape(due_text)}</div>'
                '</div>'
            )
        if not cards:
            cards.append(f'<div class="cmd-muted">{escape(t(lang, "na"))}</div>')
        lanes.append(
            '<div class="cmd-workflow-lane">'
            f'<div class="cmd-workflow-lane-title"><span>{escape(workflow_status_label(status, lang))}</span><strong>{len(lane_df)}</strong></div>'
            f'{"".join(cards)}'
            '</div>'
        )
    return f'<div class="cmd-workflow-board">{"".join(lanes)}</div>'


def render_enterprise_summary_html(
    users: pd.DataFrame,
    approvals: pd.DataFrame,
    notifications: pd.DataFrame,
    outbox: pd.DataFrame,
    lang: str,
) -> str:
    """Return enterprise control-plane summary cards from security and workflow records."""
    if users.empty:
        active_users = 0
    elif "active" in users.columns:
        active_users = len(users[users["active"].fillna(1).astype(str) != "0"])
    else:
        active_users = len(users)
    pending_approvals = (
        int(approvals["status"].astype(str).str.lower().eq("pending").sum())
        if not approvals.empty and "status" in approvals.columns
        else 0
    )
    queued_notifications = (
        int(notifications["status"].astype(str).str.lower().eq("queued").sum())
        if not notifications.empty and "status" in notifications.columns
        else 0
    )
    queued_outbox = (
        int(outbox["status"].astype(str).str.lower().eq("queued").sum())
        if not outbox.empty and "status" in outbox.columns
        else 0
    )
    return (
        '<div class="cmd-workflow-grid">'
        f'{workflow_metric_card(t(lang, "role_backed_users"), str(active_users), t(lang, "status"), "ok" if active_users else "warn", TRUST_LIVE, lang)}'
        f'{workflow_metric_card(t(lang, "pending_approvals"), str(pending_approvals), t(lang, "approval_policy"), "warn" if pending_approvals else "ok", TRUST_LIVE, lang)}'
        f'{workflow_metric_card(t(lang, "notification_queue"), str(queued_notifications), t(lang, "queued_status"), "info" if queued_notifications else "ok", TRUST_LIVE, lang)}'
        f'{workflow_metric_card(t(lang, "integration_outbox"), str(queued_outbox), t(lang, "dispatch_queue"), "warn" if queued_outbox else "ok", TRUST_LIVE, lang)}'
        '</div>'
    )


def render_connector_health_html(outbox: pd.DataFrame, lang: str) -> str:
    """Return CMMS/MES connector health cards from outbox status records."""
    cards: list[str] = []
    status_labels = {
        "sent": t(lang, "sent_status"),
        "queued": t(lang, "queued_status"),
        "retrying": t(lang, "retrying_status"),
        "failed": t(lang, "failed_status"),
        "dead_letter": t(lang, "dead_letter_status"),
        "not_configured": t(lang, "not_configured_status"),
    }
    for target, title_key in [("cmms", "cmms_connector"), ("mes", "mes_connector")]:
        if outbox.empty or "target_system" not in outbox.columns or "status" not in outbox.columns:
            counts = pd.Series(dtype=int)
        else:
            target_rows = outbox[outbox["target_system"].astype(str).str.lower() == target]
            counts = target_rows["status"].astype(str).str.lower().value_counts()
        details = []
        for status, label in status_labels.items():
            count = int(counts.get(status, 0))
            if count:
                details.append(f"{label}: {count}")
        sub = " | ".join(details) if details else t(lang, "not_configured_status")
        tone = "ok"
        if int(counts.get("failed", 0)) or int(counts.get("dead_letter", 0)):
            tone = "risk"
        elif int(counts.get("retrying", 0)) or int(counts.get("not_configured", 0)) or not details:
            tone = "warn"
        cards.append(
            workflow_metric_card(
                t(lang, title_key),
                str(int(counts.sum())) if not counts.empty else "0",
                sub,
                tone,
                TRUST_LIVE if details else TRUST_MODEL_UNAVAILABLE,
                lang,
            )
        )
    return f'<div class="cmd-workflow-grid">{"".join(cards)}</div>'


def page_operations_workflow(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render operations workflow case-management page."""
    st.header(t(lang, "page_workflow_header"))
    st.caption(t(lang, "workflow_subtitle"))
    st.info(t(lang, "workflow_boundary"))

    if st.button(t(lang, "sync_workflow")):
        result = sync_workflow_cases(lang)
        st.success(t(lang, "workflow_synced", **result))
        st.cache_data.clear()
        st.rerun()

    cases = tables.get("cases", pd.DataFrame()).copy()
    events = tables.get("case_events", pd.DataFrame()).copy()
    users = tables.get("users", pd.DataFrame()).copy()
    approvals = tables.get("approvals", pd.DataFrame()).copy()
    notifications = tables.get("notifications", pd.DataFrame()).copy()
    outbox = tables.get("outbox", pd.DataFrame()).copy()

    st.subheader(t(lang, "enterprise_controls"))
    st.caption(t(lang, "approval_policy_body"))
    st.markdown(render_enterprise_summary_html(users, approvals, notifications, outbox, lang), unsafe_allow_html=True)
    st.caption(t(lang, "connector_health"))
    st.markdown(render_connector_health_html(outbox, lang), unsafe_allow_html=True)

    control_tabs = st.tabs([t(lang, "approval_policy"), t(lang, "notification_queue"), t(lang, "integration_outbox")])
    with control_tabs[0]:
        if approvals.empty:
            show_empty(t(lang, "na"))
        else:
            display_dataframe(approvals.head(20), lang, width="stretch", hide_index=True)
    with control_tabs[1]:
        if notifications.empty:
            show_empty(t(lang, "na"))
        else:
            display_dataframe(notifications.head(20), lang, width="stretch", hide_index=True)
    with control_tabs[2]:
        if outbox.empty:
            show_empty(t(lang, "na"))
        else:
            display_dataframe(outbox.head(20), lang, width="stretch", hide_index=True)

    if cases.empty:
        show_empty(t(lang, "no_workflow_cases"))
        return

    open_cases = cases[~cases["status"].astype(str).str.lower().eq("resolved")]
    critical_high = cases[cases["severity"].astype(str).str.lower().isin(["critical", "high"])]
    unassigned = open_cases[open_cases["owner"].fillna("").astype(str).str.lower().isin(["", "unassigned", "none"])]
    due_cases = pd.DataFrame()
    if "due_at" in open_cases.columns:
        due_at = pd.to_datetime(open_cases["due_at"], errors="coerce", utc=True)
        due_cases = open_cases[due_at.notna() & (due_at <= pd.Timestamp.now(tz="UTC"))]

    st.markdown(
        '<div class="cmd-workflow-grid">'
        f'{workflow_metric_card(t(lang, "open_cases"), str(len(open_cases)), t(lang, "event_trail_ready"), "warn" if len(open_cases) else "ok", TRUST_LIVE, lang)}'
        f'{workflow_metric_card(t(lang, "critical_high_cases"), str(len(critical_high)), t(lang, "severity"), "risk" if len(critical_high) else "ok", TRUST_LIVE, lang)}'
        f'{workflow_metric_card(t(lang, "unassigned_cases"), str(len(unassigned)), t(lang, "owner"), "warn" if len(unassigned) else "ok", TRUST_LIVE, lang)}'
        f'{workflow_metric_card(t(lang, "due_cases"), str(len(due_cases)), t(lang, "due_at"), "risk" if len(due_cases) else "ok", TRUST_LIVE, lang)}'
        '</div>',
        unsafe_allow_html=True,
    )

    st.subheader(t(lang, "workflow_board"))
    st.markdown(render_workflow_board_html(cases, lang), unsafe_allow_html=True)

    st.subheader(t(lang, "case_details"))
    case_options = cases["case_id"].astype(str).tolist()
    selected_case = st.selectbox(
        t(lang, "select_case"),
        case_options,
        format_func=lambda case_id: f"{case_id} - {cases.loc[cases['case_id'].astype(str) == case_id, 'title'].iloc[0]}",
    )
    case_row = cases[cases["case_id"].astype(str) == selected_case].iloc[0]
    detail_left, detail_right = st.columns([.95, 1.2], gap="small")
    with detail_left:
        detail_cols = [
            col
            for col in ["case_id", "title", "severity", "status", "owner", "machine_id", "line_id", "station_id", "source_type", "signal_score", "condition_score", "last_seen_at", "due_at", "next_action"]
            if col in cases.columns
        ]
        display_dataframe(pd.DataFrame([case_row[detail_cols].to_dict()]), lang, width="stretch", hide_index=True)
        evidence = case_row.get("evidence_json", "")
        if isinstance(evidence, str) and evidence.strip():
            try:
                st.json(json.loads(evidence))
            except Exception:
                st.code(evidence)
    with detail_right:
        current_status = str(case_row.get("status", "new")).lower()
        current_owner = str(case_row.get("owner") or "unassigned")
        current_action = str(case_row.get("next_action") or "")
        status_index = WORKFLOW_STATUS_ORDER.index(current_status) if current_status in WORKFLOW_STATUS_ORDER else 0
        with st.form("workflow_case_update_form"):
            new_status = st.selectbox(
                t(lang, "status"),
                WORKFLOW_STATUS_ORDER,
                index=status_index,
                format_func=lambda value: workflow_status_label(value, lang),
            )
            new_owner = st.text_input(t(lang, "owner"), value=current_owner)
            new_action = st.text_area(t(lang, "next_action"), value=current_action, height=100)
            note = st.text_area(t(lang, "operator_note"), height=90)
            submitted = st.form_submit_button(t(lang, "update_case"))
        if submitted:
            if operations_repository is None:
                st.error(t(lang, "query_failed", error="workflow repository unavailable"))
            else:
                try:
                    operations_repository.update_operational_case(
                        selected_case,
                        {"status": new_status, "owner": new_owner, "next_action": new_action},
                        get_db_path(),
                        actor="dashboard",
                        note=note,
                    )
                    st.success(t(lang, "case_updated"))
                    st.cache_data.clear()
                    st.rerun()
                except PermissionError as exc:
                    st.error(t(lang, "query_failed", error=exc))

        selected_events = events[events["case_id"].astype(str) == selected_case] if not events.empty and "case_id" in events.columns else pd.DataFrame()
        st.caption(t(lang, "event_log"))
        if selected_events.empty:
            show_empty(t(lang, "na"))
        else:
            display_dataframe(selected_events.head(25), lang, width="stretch", hide_index=True)

        st.caption(t(lang, "enterprise_actions"))
        if operations_repository is None:
            st.error(t(lang, "query_failed", error="workflow repository unavailable"))
        else:
            qualified_users = pd.DataFrame()
            if not users.empty and {"user_id", "role"} <= set(users.columns):
                qualified_users = users[users["role"].astype(str).str.lower().isin(["operator", "supervisor", "admin"])].copy()
            owner_options = qualified_users["user_id"].astype(str).tolist() if not qualified_users.empty else ["operator", "supervisor"]

            with st.form(f"case_owner_form_{selected_case}"):
                owner_user = st.selectbox(t(lang, "owner"), owner_options, key=f"owner_user_{selected_case}")
                owner_role = st.selectbox(t(lang, "owners_label"), ["primary", "secondary", "maintenance"], key=f"owner_role_{selected_case}")
                owner_submitted = st.form_submit_button(t(lang, "assign_owner"))
            if owner_submitted:
                try:
                    operations_repository.assign_case_owner(
                        selected_case,
                        owner_user,
                        owner_role,
                        get_db_path(),
                        assigned_by="supervisor",
                    )
                    st.success(t(lang, "assignment_saved"))
                    st.cache_data.clear()
                    st.rerun()
                except (PermissionError, KeyError, ValueError) as exc:
                    st.error(t(lang, "query_failed", error=exc))

            with st.form(f"case_approval_request_form_{selected_case}"):
                approval_type = st.selectbox(t(lang, "approval_type"), ["resolve_case", "external_dispatch"], key=f"approval_type_{selected_case}")
                approval_reason = st.text_area(t(lang, "reason"), height=80, key=f"approval_reason_{selected_case}")
                approval_submitted = st.form_submit_button(t(lang, "request_approval"))
            if approval_submitted:
                try:
                    operations_repository.request_case_approval(
                        selected_case,
                        approval_type,
                        "operator",
                        get_db_path(),
                        reason=approval_reason,
                    )
                    st.success(t(lang, "approval_requested"))
                    st.cache_data.clear()
                    st.rerun()
                except (PermissionError, KeyError, ValueError) as exc:
                    st.error(t(lang, "query_failed", error=exc))

            selected_approvals = (
                approvals[
                    (approvals["case_id"].astype(str) == selected_case)
                    & (approvals["status"].astype(str).str.lower() == "pending")
                ].copy()
                if not approvals.empty and {"case_id", "status", "approval_id"} <= set(approvals.columns)
                else pd.DataFrame()
            )
            if not selected_approvals.empty:
                with st.form(f"case_approval_decision_form_{selected_case}"):
                    approval_id = st.selectbox(
                        t(lang, "approval_policy"),
                        selected_approvals["approval_id"].astype(str).tolist(),
                        key=f"approval_id_{selected_case}",
                    )
                    decision = st.selectbox(t(lang, "decision"), ["approved", "rejected"], key=f"decision_{selected_case}")
                    decision_note = st.text_area(t(lang, "decision_note"), height=80, key=f"decision_note_{selected_case}")
                    decision_submitted = st.form_submit_button(t(lang, "decide_approval"))
                if decision_submitted:
                    try:
                        operations_repository.decide_case_approval(
                            approval_id,
                            decision,
                            "supervisor",
                            get_db_path(),
                            note=decision_note,
                        )
                        st.success(t(lang, "approval_decided"))
                        st.cache_data.clear()
                        st.rerun()
                    except (PermissionError, KeyError, ValueError) as exc:
                        st.error(t(lang, "query_failed", error=exc))

            with st.form(f"case_external_dispatch_form_{selected_case}"):
                target_system = st.selectbox(t(lang, "target_system"), ["cmms", "mes"], key=f"target_system_{selected_case}")
                dispatch_submitted = st.form_submit_button(t(lang, "dispatch_external"))
            if dispatch_submitted:
                try:
                    operations_repository.dispatch_case_to_external(
                        selected_case,
                        target_system,
                        "supervisor",
                        get_db_path(),
                    )
                    st.success(t(lang, "dispatch_queued"))
                    st.cache_data.clear()
                    st.rerun()
                except (PermissionError, KeyError, ValueError) as exc:
                    st.error(t(lang, "query_failed", error=exc))


def page_data_acquisition_status(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render data acquisition status page."""
    st.header(t(lang, "page2_header"))

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
    freshness_trust = TRUST_LIVE if last_received is not None else TRUST_REPLAY
    render_metric_with_trust(c1, t(lang, "last_received_timestamp"), str(last_received) if last_received is not None else t(lang, "na"), freshness_trust, lang)
    render_metric_with_trust(c2, t(lang, "successful_ingestion_count"), successful_ingestion_count, TRUST_LIVE, lang)
    render_metric_with_trust(c3, t(lang, "failed_ingestion_count"), failed_ingestion_count, TRUST_LIVE, lang)
    render_metric_with_trust(c4, t(lang, "buffered_records_proxy"), buffered_proxy, TRUST_DERIVED, lang)
    render_metric_with_trust(c5, t(lang, "delayed_readings"), delayed_readings, TRUST_NOT_CHECKED if issues.empty else TRUST_LIVE, lang)

    st.subheader(t(lang, "collector_status"))
    if sensor.empty and production.empty:
        show_empty(
            t(lang, "no_ingested_data"),
            "bash scripts/run_api.sh\ncd acquisition-csharp/SensorCollector && dotnet run",
        )
    else:
        freshness = "active"
        if last_received is not None:
            age_seconds = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(last_received)).total_seconds()
            freshness = "active" if age_seconds < 120 else "stale"
        render_status_pills([(t(lang, "collector_status_proxy", state=t(lang, freshness)), "ok" if freshness == "active" else "warn")])
        st.caption(t(lang, "collector_status_note"))

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
            plot_line(counts, "minute", "records", color="type", title=t(lang, "ingestion_records_per_minute"), lang=lang)

    st.subheader(t(lang, "acquisition_logs"))
    if logs.empty:
        show_empty(t(lang, "no_acquisition_logs"))
    else:
        display_dataframe(logs.head(200), lang, width="stretch")


def page_line_monitoring(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render line monitoring page."""
    st.header(t(lang, "page3_header"))
    production = tables["production"]

    if production.empty:
        show_empty(
            t(lang, "no_production_events"),
            "bash scripts/run_api.sh\ncd acquisition-csharp/SensorCollector && dotnet run",
        )
        return

    filter_cols = st.columns([1, 1, 1, 1])
    lines = sorted(production["line_id"].dropna().unique()) if "line_id" in production.columns else []
    selected_line = filter_cols[0].selectbox(t(lang, "select_line"), lines) if lines else None
    line_df = production[production["line_id"] == selected_line].copy() if selected_line else production.copy()
    stations = [t(lang, "all_stations")]
    if "station_id" in line_df.columns:
        stations.extend(sorted(line_df["station_id"].dropna().astype(str).unique().tolist()))
    selected_station = filter_cols[1].selectbox(t(lang, "select_station"), stations)
    if selected_station != t(lang, "all_stations") and "station_id" in line_df.columns:
        line_df = line_df[line_df["station_id"].astype(str) == selected_station].copy()
    window_label = filter_cols[2].selectbox(t(lang, "chart_time_window"), chart_window_options(lang), index=2)
    focus_label = filter_cols[3].selectbox(
        t(lang, "chart_focus"),
        [t(lang, "priority_stations"), t(lang, "all_stations_in_chart")],
        index=0,
    )
    window_hours = hours_from_window_label(window_label)
    line_df = line_df.sort_values("timestamp")
    chart_df = line_df.copy()
    chart_color = "station_id" if selected_station == t(lang, "all_stations") and "station_id" in chart_df.columns else None
    if chart_color and focus_label == t(lang, "priority_stations"):
        focus_groups = priority_groups_for_chart(chart_df, "station_id", limit=2)
        if focus_groups:
            chart_df = chart_df[chart_df["station_id"].astype(str).isin(focus_groups)].copy()
        st.caption(t(lang, "chart_focus_caption"))

    c1, c2, c3, c4 = st.columns(4)
    render_metric_with_trust(c1, t(lang, "events"), len(line_df), TRUST_LIVE, lang)
    render_metric_with_trust(c2, t(lang, "avg_cycle_time"), format_metric(safe_mean(line_df, "cycle_time_sec"), "s", lang=lang), TRUST_LIVE, lang)
    render_metric_with_trust(c3, t(lang, "avg_station_yield"), format_metric(safe_mean(line_df, "station_yield"), decimals=4, lang=lang), TRUST_LIVE, lang)
    render_metric_with_trust(c4, t(lang, "total_downtime_min"), format_metric(pd.to_numeric(line_df.get("downtime_minutes", pd.Series(dtype=float)), errors="coerce").sum(), decimals=2, lang=lang), TRUST_DERIVED, lang)

    st.subheader(t(lang, "throughput_vs_target"))
    if "target_throughput" in line_df.columns and "throughput_count" in line_df.columns:
        target = safe_mean(line_df, "target_throughput")
        thresholds = [(target, t(lang, "lower_threshold"), "#f4ce31")] if target is not None else []
        plot_line(chart_df, "timestamp", "throughput_count", color=chart_color, title=t(lang, "throughput_vs_target"), lang=lang, time_window_hours=window_hours, thresholds=thresholds)

    st.subheader(t(lang, "cycle_time_trend"))
    plot_line(chart_df, "timestamp", "cycle_time_sec", color=chart_color, title=t(lang, "cycle_time_trend"), lang=lang, time_window_hours=window_hours, thresholds=[(6.0, t(lang, "upper_threshold"), "#ff5148")])

    st.subheader(t(lang, "station_yield_trend"))
    plot_line(chart_df, "timestamp", "station_yield", color=chart_color, title=t(lang, "station_yield_trend"), lang=lang, time_window_hours=window_hours, thresholds=[(0.95, t(lang, "lower_threshold"), "#f4ce31")])

    st.subheader(t(lang, "reject_defect_rate_trend"))
    y_col = "defect_rate" if "defect_rate" in line_df.columns else "reject_count"
    plot_line(chart_df, "timestamp", y_col, color=chart_color, title=t(lang, "reject_defect_rate_trend"), lang=lang, time_window_hours=window_hours, thresholds=[(0.03, t(lang, "upper_threshold"), "#ff5148")] if y_col == "defect_rate" else None)

    st.subheader(t(lang, "micro_stops_downtime"))
    c1, c2 = st.columns(2)
    with c1:
        plot_line(chart_df, "timestamp", "micro_stop_count", color=chart_color, title=t(lang, "micro_stop_count"), lang=lang, time_window_hours=window_hours, thresholds=[(4.0, t(lang, "upper_threshold"), "#f4ce31")])
    with c2:
        plot_line(chart_df, "timestamp", "downtime_minutes", color=chart_color, title=t(lang, "downtime_minutes"), lang=lang, time_window_hours=window_hours, thresholds=[(1.0, t(lang, "upper_threshold"), "#ff5148")])


def page_equipment_health(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render equipment health page."""
    st.header(t(lang, "page4_header"))
    sensor = tables["sensor"]
    production = tables["production"]
    predictions = tables["predictions"]
    snapshot = build_machine_snapshot(sensor, production, predictions, lang)

    if sensor.empty:
        show_empty(t(lang, "no_sensor_readings"))
        return

    filter_cols = st.columns([1, 1])
    machines = sorted(sensor["machine_id"].dropna().unique()) if "machine_id" in sensor.columns else []
    selected_machine = filter_cols[0].selectbox(t(lang, "select_machine"), machines) if machines else None
    window_label = filter_cols[1].selectbox(t(lang, "chart_time_window"), chart_window_options(lang), index=2)
    window_hours = hours_from_window_label(window_label)
    if not selected_machine:
        show_empty(t(lang, "no_machine_ids"))
        return

    sensor_df = sensor[sensor["machine_id"] == selected_machine].sort_values("timestamp")
    sensor_chart_df = prepare_timeseries(sensor_df, timestamp_col="timestamp", hours=window_hours, max_points=900)
    pred_df = predictions[predictions["machine_id"] == selected_machine].sort_values("timestamp") if not predictions.empty and "machine_id" in predictions.columns else pd.DataFrame()
    latest_pred = pred_df.tail(1)
    snapshot_row = snapshot[snapshot["machine_id"] == selected_machine].tail(1) if not snapshot.empty else pd.DataFrame()
    selected_condition = snapshot_row["condition_score"].iloc[0] if not snapshot_row.empty and "condition_score" in snapshot_row.columns else None
    selected_anomaly = snapshot_row["derived_anomaly_index"].iloc[0] if not snapshot_row.empty and "derived_anomaly_index" in snapshot_row.columns else None
    selected_risk = snapshot_row["risk_level"].iloc[0] if not snapshot_row.empty and "risk_level" in snapshot_row.columns else t(lang, "na")

    c1, c2, c3, c4 = st.columns(4)
    model_metric_trust = TRUST_LIVE if not latest_pred.empty else TRUST_MODEL_UNAVAILABLE
    render_metric_with_trust(c1, t(lang, "failure_probability"), format_metric(latest_pred["failure_probability"].iloc[0] if not latest_pred.empty and "failure_probability" in latest_pred.columns else None, lang=lang), model_metric_trust, lang)
    render_metric_with_trust(c2, t(lang, "rul_hours"), format_metric(latest_pred["rul_estimate_hours"].iloc[0] if not latest_pred.empty and "rul_estimate_hours" in latest_pred.columns else None, lang=lang), model_metric_trust, lang)
    render_metric_with_trust(c3, t(lang, "condition_score"), format_metric(selected_condition, lang=lang), TRUST_DERIVED, lang)
    render_metric_with_trust(c4, t(lang, "risk_level"), latest_pred["risk_level"].iloc[0] if not latest_pred.empty and "risk_level" in latest_pred.columns else selected_risk, model_metric_trust if not latest_pred.empty else TRUST_DERIVED, lang)

    tabs = st.tabs([t(lang, "detail_tab_overview"), t(lang, "detail_tab_signals"), t(lang, "detail_tab_events"), t(lang, "detail_tab_context")])

    with tabs[0]:
        render_notice(t(lang, "investigation_panel"), t(lang, "investigation_note"))
        if not snapshot_row.empty:
            display_dataframe(
                snapshot_row[["machine_id", "line_station", "condition_score", "derived_anomaly_index", "risk_level", "dominant_signal", "source"]],
                lang,
                width="stretch",
                hide_index=True,
            )
        if selected_anomaly is not None:
            render_status_pills([(t(lang, "derived_anomaly_index") + f": {selected_anomaly:.3f}", "warn" if selected_anomaly >= 0.5 else "ok")])

    with tabs[1]:
        st.subheader(t(lang, "sensor_trends"))
        sensor_cols = [c for c in ["vibration_rms", "process_temperature", "motor_current", "torque", "tool_wear"] if c in sensor_chart_df.columns]
        if sensor_cols:
            plot_line(sensor_chart_df, "timestamp", sensor_cols, color="station_id" if "station_id" in sensor_chart_df.columns else None, title=t(lang, "sensor_trends_machine", machine=selected_machine), lang=lang, time_window_hours=None, thresholds=[(70.0, t(lang, "upper_threshold"), "#ff5148")])
        machine_timeline = prepare_timeseries(build_condition_timeline(sensor, selected_machine, limit=500), timestamp_col="timestamp", hours=window_hours, max_points=500)
        render_condition_timeline(machine_timeline, lang)

    with tabs[2]:
        st.subheader(t(lang, "recent_machine_records"))
        timeline = build_condition_timeline(sensor, selected_machine, limit=80)
        cols = [c for c in ["timestamp", "machine_id", "line_id", "station_id", "condition_score", "derived_anomaly_index", "vibration_rms", "tool_wear", "process_temperature"] if c in timeline.columns]
        display_dataframe(timeline[cols].tail(50), lang, width="stretch", hide_index=True)
        if not pred_df.empty:
            st.subheader(t(lang, "recent_prediction_history"))
            display_dataframe(pred_df.tail(50), lang, width="stretch")

    with tabs[3]:
        st.subheader(t(lang, "recommended_action"))
        if latest_pred.empty:
            show_empty(t(lang, "no_machine_prediction"), "python backend-python/src/models/train_all.py")
        else:
            action = latest_pred.get("recommended_action", pd.Series([t(lang, "na")])).iloc[0]
            hint = latest_pred.get("diagnostic_hint", pd.Series([t(lang, "na")])).iloc[0]
            st.markdown(html_card(t(lang, "recommended_maintenance_action"), action, t(lang, "recommended_maintenance_caption")), unsafe_allow_html=True)
            st.caption(t(lang, "diagnostic_hint"))
            st.info(hint)
        if not sensor_df.empty:
            st.caption(t(lang, "latest_sensor_record"))
            display_dataframe(sensor_df.tail(1), lang, width="stretch", hide_index=True)
        if not production.empty and not snapshot_row.empty:
            prod_df = production[
                (production["line_id"] == snapshot_row["line_id"].iloc[0])
                & (production["station_id"] == snapshot_row["station_id"].iloc[0])
            ].sort_values("timestamp")
            if not prod_df.empty:
                st.caption(t(lang, "latest_production_record"))
                display_dataframe(prod_df.tail(1), lang, width="stretch", hide_index=True)


def page_process_anomaly(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render process anomaly page."""
    st.header(t(lang, "page5_header"))
    sensor = tables["sensor"]
    alerts = tables["alerts"]
    predictions = tables["predictions"]
    hints = tables["hints"]
    window_label = st.selectbox(t(lang, "chart_time_window"), chart_window_options(lang), index=2)
    window_hours = hours_from_window_label(window_label)
    condition_timeline = prepare_timeseries(build_condition_timeline(sensor, limit=700), timestamp_col="timestamp", group_col="machine_id", hours=window_hours, max_points=700)
    if not condition_timeline.empty:
        condition_timeline["dominant_signal"] = condition_timeline.apply(lambda row: dominant_signal(row, lang), axis=1)
    derived_watchlist = pd.DataFrame()
    if not condition_timeline.empty and "derived_anomaly_index" in condition_timeline.columns:
        derived_watchlist = (
            condition_timeline[condition_timeline["derived_anomaly_index"] >= 0.5]
            .sort_values(["derived_anomaly_index", "timestamp"], ascending=[False, False])
            .head(200)
        )
        if derived_watchlist.empty:
            derived_watchlist = condition_timeline.sort_values(["derived_anomaly_index", "timestamp"], ascending=[False, False]).head(40)

    anomaly_flags = int(pd.to_numeric(predictions.get("anomaly_flag", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not predictions.empty else 0
    if anomaly_flags == 0 and not derived_watchlist.empty:
        anomaly_flags = int((derived_watchlist["derived_anomaly_index"] >= 0.5).sum())

    c1, c2, c3 = st.columns(3)
    render_metric_with_trust(c1, t(lang, "alerts"), len(alerts), TRUST_LIVE if not alerts.empty else TRUST_MODEL_UNAVAILABLE, lang)
    render_metric_with_trust(c2, t(lang, "anomaly_flags"), anomaly_flags, TRUST_LIVE if not predictions.empty else TRUST_DERIVED, lang)
    render_metric_with_trust(c3, t(lang, "diagnostic_hints"), len(hints) if not hints.empty else len(derived_watchlist), TRUST_LIVE if not hints.empty else TRUST_DERIVED, lang)

    st.subheader(t(lang, "anomaly_timeline"))
    if not predictions.empty and "anomaly_score" in predictions.columns:
        plot_line(predictions.sort_values("timestamp"), "timestamp", "anomaly_score", color="station_id" if "station_id" in predictions.columns else None, title=t(lang, "anomaly_score_timeline"), lang=lang, time_window_hours=window_hours, thresholds=[(0.5, t(lang, "upper_threshold"), "#f4ce31"), (0.75, t(lang, "upper_threshold"), "#ff5148")])
    elif not alerts.empty:
        plot_line(alerts.sort_values("timestamp"), "timestamp", "anomaly_score", color="station_id" if "station_id" in alerts.columns else None, title=t(lang, "anomaly_alert_timeline"), lang=lang, time_window_hours=window_hours, thresholds=[(0.5, t(lang, "upper_threshold"), "#f4ce31"), (0.75, t(lang, "upper_threshold"), "#ff5148")])
    elif not condition_timeline.empty:
        render_notice(t(lang, "derived_diagnostic_hint"), t(lang, "model_alerts_unavailable"))
        render_condition_timeline(condition_timeline, lang)
    else:
        show_empty(t(lang, "no_anomaly_data"))

    st.subheader(t(lang, "affected_line_station"))
    if alerts.empty:
        if derived_watchlist.empty:
            show_empty(t(lang, "no_derived_anomaly_records"))
        else:
            st.caption(t(lang, "derived_anomaly_watchlist_caption"))
            cols = [
                c
                for c in [
                    "timestamp",
                    "machine_id",
                    "line_id",
                    "station_id",
                    "condition_score",
                    "derived_anomaly_index",
                    "dominant_signal",
                    "vibration_rms",
                    "tool_wear",
                    "process_temperature",
                    "motor_current",
                    "torque",
                ]
                if c in derived_watchlist.columns
            ]
            display_dataframe(derived_watchlist[cols], lang, width="stretch", hide_index=True)
    else:
        cols = [c for c in ["timestamp", "machine_id", "line_id", "station_id", "anomaly_score", "severity", "message", "source"] if c in alerts.columns]
        display_dataframe(alerts[cols].head(200), lang, width="stretch")

    st.subheader(t(lang, "diagnostic_hints"))
    source = hints if not hints.empty else predictions
    if source.empty and not derived_watchlist.empty:
        source = derived_watchlist.copy()
        source["diagnostic_hint"] = source.apply(
            lambda row: f"{t(lang, 'dominant_signal')}: {row.get('dominant_signal', t(lang, 'na'))}; {t(lang, 'condition_score')}: {format_metric(row.get('condition_score'), decimals=1, lang=lang)}",
            axis=1,
        )
        source["recommended_action"] = t(lang, "derived_recommended_action")
    if source.empty:
        show_empty(t(lang, "no_diagnostic_hints"))
    else:
        cols = [c for c in ["timestamp", "machine_id", "line_id", "station_id", "hint", "diagnostic_hint", "recommended_action"] if c in source.columns]
        display_dataframe(source[cols].head(200), lang, width="stretch")


def page_data_quality(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render data quality page."""
    st.header(t(lang, "page6_header"))
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
    quality_trust = TRUST_LIVE if not issues.empty else TRUST_NOT_CHECKED
    render_metric_with_trust(c1, t(lang, "missing_values"), missing_values, quality_trust, lang)
    render_metric_with_trust(c2, t(lang, "duplicate_timestamps"), duplicates, quality_trust, lang)
    render_metric_with_trust(c3, t(lang, "stuck_sensor"), stuck, quality_trust, lang)
    render_metric_with_trust(c4, t(lang, "timestamp_gaps"), gaps, quality_trust, lang)
    render_metric_with_trust(c5, t(lang, "sensor_dropout"), dropout, quality_trust, lang)
    render_metric_with_trust(c6, t(lang, "impossible_values"), impossible, quality_trust, lang)

    if issues.empty:
        show_empty(
            t(lang, "no_quality_issues"),
            "python backend-python/src/data/preprocessing.py",
        )
        if not sensor.empty or not production.empty:
            st.caption(t(lang, "raw_tables_no_quality"))
        return

    st.subheader(t(lang, "issue_counts_by_type"))
    counts = issues.groupby("issue_type").size().reset_index(name="count").sort_values("count", ascending=False)
    plot_bar(counts, "issue_type", "count", title=t(lang, "data_quality_issues_by_type"), lang=lang)

    st.subheader(t(lang, "issue_severity"))
    if "severity" in issues.columns:
        severity = issues.groupby("severity").size().reset_index(name="count")
        plot_bar(severity, "severity", "count", title=t(lang, "issue_severity"), lang=lang)

    st.subheader(t(lang, "recent_quality_issues"))
    cols = [c for c in ["detected_at", "issue_type", "severity", "entity_type", "machine_id", "line_id", "station_id", "timestamp", "details_json"] if c in issues.columns]
    display_dataframe(issues[cols].head(300), lang, width="stretch")


def page_model_training_registry(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render model training and registry page."""
    st.header(t(lang, "page7_header"))
    model_runs = tables["models"]

    st.subheader(t(lang, "training_command"))
    st.markdown(
        f'<div class="smop-section-note">{escape(t(lang, "training_note"))}</div>',
        unsafe_allow_html=True,
    )
    st.code("python backend-python/src/models/train_all.py", language="bash")

    if st.button(t(lang, "show_training_reminder")):
        st.success(t(lang, "training_reminder"))

    if model_runs.empty:
        show_empty(t(lang, "no_model_runs"))
        return

    st.subheader(t(lang, "model_runs"))
    cols = [c for c in ["id", "model_name", "model_type", "model_version", "artifact_path", "training_rows", "test_rows", "completed_at", "status"] if c in model_runs.columns]
    display_dataframe(model_runs[cols], lang, width="stretch")

    st.subheader(t(lang, "metrics"))
    selected_id = st.selectbox(t(lang, "select_model_run_id"), model_runs["id"].tolist())
    selected = model_runs[model_runs["id"] == selected_id].iloc[0]
    metrics = load_metrics_json_from_row(selected)
    if metrics:
        st.json(metrics)
    else:
        st.info(t(lang, "no_metrics_json"))

    st.subheader(t(lang, "feature_importance"))
    artifact_path = selected.get("artifact_path")
    if isinstance(artifact_path, str) and artifact_path:
        show_feature_importance(Path(artifact_path), lang)
    else:
        st.info(t(lang, "no_artifact_path"))


def show_feature_importance(artifact_path: Path, lang: str) -> None:
    """Attempt to load a joblib model and display feature importances if available."""
    try:
        import joblib
    except Exception:
        st.info(t(lang, "joblib_missing"))
        return

    if not artifact_path.is_absolute():
        artifact_path = project_root() / artifact_path
    if not artifact_path.exists():
        st.info(t(lang, "model_artifact_not_found", path=artifact_path))
        return

    try:
        bundle = joblib.load(artifact_path)
        model = bundle.get("model")
        feature_columns = bundle.get("feature_columns", [])
        estimator = getattr(model, "named_steps", {}).get("model", model)
        importances = getattr(estimator, "feature_importances_", None)
        if importances is None:
            st.info(t(lang, "no_feature_importance"))
            return
        importance_df = pd.DataFrame({"feature": feature_columns, "importance": importances}).sort_values("importance", ascending=False).head(25)
        display_dataframe(importance_df, lang, width="stretch")
        plot_bar(importance_df, "feature", "importance", title=t(lang, "top_feature_importance"), lang=lang)
    except Exception as exc:
        st.warning(t(lang, "feature_importance_failed", error=exc))


def page_reports_edge_deployment(tables: dict[str, pd.DataFrame], lang: str) -> None:
    """Render reports and edge deployment page."""
    st.header(t(lang, "page8_header"))

    sensor = tables["sensor"]
    production = tables["production"]
    predictions = tables["predictions"]
    alerts = tables["alerts"]
    issues = tables["issues"]
    model_runs = tables["models"]

    st.subheader(t(lang, "export_csv"))
    c1, c2, c3 = st.columns(3)
    with c1:
        download_dataframe(predictions, "predictions_export.csv", t(lang, "predictions"), lang)
    with c2:
        download_dataframe(alerts, "anomaly_alerts_export.csv", t(lang, "alerts_label"), lang)
    with c3:
        download_dataframe(issues, "data_quality_issues_export.csv", t(lang, "quality_issues_label"), lang)

    st.subheader(t(lang, "markdown_report"))
    report_md = make_markdown_report(sensor, production, predictions, alerts, issues, model_runs, lang=lang)
    st.download_button(
        t(lang, "download_markdown_report"),
        data=report_md.encode("utf-8"),
        file_name="smart_manufacturing_ai_operations_report.md",
        mime="text/markdown",
    )

    if st.button(t(lang, "save_report")):
        report_path = project_root() / "reports" / "dashboard_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding="utf-8")
        st.success(t(lang, "saved_report", path=report_path))

    st.subheader(t(lang, "edge_architecture"))
    st.markdown(t(lang, "edge_architecture_text"))

    st.subheader(t(lang, "limitations"))
    st.warning(t(lang, "limitations_text"))


def main() -> None:
    """Streamlit entrypoint."""
    lang = render_header()
    tables = load_all_tables(lang)
    render_command_topbar(tables, lang)

    pages = {
        "executive": page_executive_overview,
        "workflow": page_operations_workflow,
        "acquisition": page_data_acquisition_status,
        "line": page_line_monitoring,
        "equipment": page_equipment_health,
        "anomaly": page_process_anomaly,
        "quality": page_data_quality,
        "models": page_model_training_registry,
        "reports": page_reports_edge_deployment,
    }

    selected_page = st.sidebar.radio(
        t(lang, "pages"),
        list(pages),
        format_func=lambda key: t(lang, f"page_{key}"),
    )
    render_sidebar_data_source(tables, lang)
    pages[selected_page](tables, lang)


if __name__ == "__main__":
    main()
