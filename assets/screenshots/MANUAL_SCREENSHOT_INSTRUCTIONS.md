# Manual Dashboard Screenshot Instructions

Automated capture requires Playwright and a running Streamlit dashboard.

1. Run `bash scripts/run_full_demo.sh` to seed demo data.
2. Run `bash scripts/run_dashboard.sh`.
3. Open `http://127.0.0.1:8501`.
4. Capture each sidebar page and save as:

- `Executive Overview` -> `01_executive_overview.png`
- `Data Acquisition Status` -> `02_data_acquisition.png`
- `Line Monitoring` -> `03_line_monitoring.png`
- `Equipment Health` -> `04_equipment_health.png`
- `Process Anomaly` -> `05_anomaly_detection.png`
- `Data Quality` -> `06_data_quality.png`
- `Model Training & Registry` -> `07_model_registry.png`
- `Reports / Edge Deployment` -> `08_reports.png`

Do not use fake screenshots. Images must come from the real dashboard.
