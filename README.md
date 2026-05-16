# Smart Manufacturing AI Operations Platform

## Production-grade redesign note

This package has been upgraded to read and feel closer to a real manufacturing operations system while remaining honest that all data is simulated.

What changed in this version:

- Streamlit dashboard redesigned as an AI operations command center with production-style header, status pills, operational cards, data freshness, risk posture, and a shift-handover action queue.
- Markdown report upgraded from a generic summary into an operator handover report.
- FastAPI service hardened with lifespan startup, OpenAPI endpoint groups, and `x-request-id` response headers for troubleshooting.
- SQLite schema extended with operational indexes and read views for latest machine health and line summaries.
- Added production architecture SPEC, PlantUML diagrams, production readiness matrix, and dashboard design notes.
- Existing test suite was re-run after the redesign: `26 passed`.

## 1. Project Overview

Smart Manufacturing AI Operations Platform is an end-to-end simulated-data working prototype for industrial AI, predictive maintenance, and smart manufacturing analytics.

The system demonstrates a complete operational loop:

```text
C# Data Acquisition
-> FastAPI Ingestion
-> SQLite Storage
-> Data Quality Check
-> Feature Engineering
-> ML Training
-> Failure Prediction
-> RUL Estimation
-> Process Anomaly Detection
-> Health Score
-> Streamlit Dashboard
-> Report Export
```

The project is designed for portfolio and interview use for Industrial AI / Machine Learning Analyst roles. It shows practical software engineering, C# acquisition, Python ML, API deployment, local database design, operational dashboards, and documentation.

## 2. Why This Project

Many ML portfolio projects stop at notebooks. This project intentionally goes further:

- C# sends machine and production data through a real HTTP client.
- FastAPI receives and validates the data.
- SQLite stores records as the system of record.
- Python reads actual stored records for quality checks and training.
- Models are saved as artifacts and registered in SQLite.
- Prediction endpoints load real model artifacts.
- Streamlit reads real SQLite/API outputs and provides operational views.

This makes the project useful for interviews where the hiring manager wants evidence of production-oriented thinking, not only model experimentation.

## 3. Seagate-aligned Smart Manufacturing Use Case

This is a Seagate-aligned smart manufacturing use case, not a Seagate deployment.

The simulated profile is inspired by precision electronics manufacturing, with machine stations such as micro press, spindle test, thermal inspection, and optical inspection. The system focuses on equipment health, production stability, predictive maintenance, and process anomaly detection.

## 4. Important Data Disclaimer

This project uses simulated data only.

It does not use real Seagate data.
It does not use proprietary factory data.
It has not been deployed or validated in a real factory.
It is not a certified production control system.

Any real deployment would require real sensor integration, real maintenance labels, process-owner validation, OT/IT architecture review, cybersecurity review, and factory acceptance testing.

## 5. System Architecture

```text
Factory Edge / C# Layer
  SensorCollector
    -> MachineSensorSimulator
    -> ProductionLineSimulator
    -> ApiPublisher
    -> LocalBufferWriter
    -> RetryQueue

Python Backend
  FastAPI
    -> ingestion endpoints
    -> prediction endpoints
    -> SQLite repository

Analytics Layer
  Data quality engine
  Feature engineering
  ML training pipeline
  Model registry
  Health score and diagnostic hints

Visualization Layer
  Streamlit dashboard
  CSV / Markdown report export
```

## 6. C# Data Acquisition Layer

The C# layer is intentionally not decorative. It is a runnable .NET console application that:

- reads `appsettings.json`
- simulates sensor readings
- simulates production-line events
- uses `HttpClient`
- posts to FastAPI ingestion endpoints
- writes failed records to local JSONL buffer
- retries buffered records
- logs to console
- supports realtime and batch mode
- supports graceful Ctrl+C shutdown

Run:

```bash
cd acquisition-csharp/SensorCollector
dotnet restore
dotnet build
dotnet run
```

## 7. Production-Line Process Data

Production events include:

```text
cycle_time_sec
throughput_count
target_throughput
station_yield
reject_count
rework_count
defect_rate
micro_stop_count
downtime_minutes
wip_count
queue_length
inspection_score_proxy
process_stability_index
operator_group
```

The simulated production logic is linked to equipment condition:

```text
tool_wear increases
-> torque increases
-> motor_current increases
-> vibration increases
-> cycle_time increases
-> micro_stop_count increases
-> defect_rate increases
-> station_yield decreases
```

## 8. Python ML Pipeline

The Python layer includes:

- data quality validation
- timestamp-safe sensor/production joining
- feature engineering
- time-aware train/test split
- failure classification
- RUL regression
- IsolationForest anomaly detection
- model registry
- prediction helpers

Run preprocessing:

```bash
python backend-python/src/data/preprocessing.py
```

Run all models:

```bash
python backend-python/src/models/train_all.py
```

## 9. FastAPI Backend

FastAPI provides ingestion and inference endpoints.

Run:

```bash
bash scripts/run_api.sh
```

Main endpoints:

```text
GET  /health
POST /ingest/sensor-reading
POST /ingest/production-event
POST /ingest/batch
POST /predict/failure
POST /predict/rul
POST /detect/anomaly
GET  /data-acquisition/status
GET  /model-runs
GET  /predictions
GET  /alerts
GET  /line-health/{line_id}
```

## 10. Streamlit Dashboard

The dashboard has eight pages:

1. Executive Overview
2. Data Acquisition Status
3. Line Monitoring
4. Equipment Health
5. Process Anomaly
6. Data Quality
7. Model Training & Registry
8. Reports / Edge Deployment

Run:

```bash
streamlit run dashboard/app.py
```

or:

```bash
bash scripts/run_dashboard.sh
```

The dashboard reads SQLite data and handles empty tables without crashing.

## 11. Database Schema

SQLite is used as the local prototype system of record.

Core tables:

```text
machines
production_lines
stations
sensor_readings
production_events
data_quality_issues
data_acquisition_logs
maintenance_events
model_training_runs
model_artifacts
predictions
anomaly_alerts
diagnostic_hints
reports
system_logs
```

Tables are initialized by `backend-python/src/database/repository.py`.

## 12. ML Models

Failure classification:

- Logistic Regression baseline
- Random Forest
- GradientBoostingClassifier fallback
- optional XGBoost if installed and enabled

RUL regression:

- RandomForestRegressor
- GradientBoostingRegressor fallback

Anomaly detection:

- IsolationForest

Model artifacts:

```text
models/failure_classifier.joblib
models/rul_regressor.joblib
models/anomaly_detector.joblib
```

Metrics:

```text
models/failure_classifier_metrics.json
models/rul_regressor_metrics.json
models/anomaly_detector_metrics.json
```

## 13. Machine / Line Health Score

Health score combines:

- failure probability
- anomaly score
- tool wear index
- process drift score
- data quality penalty
- RUL penalty

Risk levels:

```text
low
medium
high
critical
```

Diagnostic hints are rule-based and explain likely operational patterns.

## 14. Edge Deployment Concept

A realistic deployment pattern would place the C# collector on an edge PC near the production line. The collector sends HTTP data to a local API service. SQLite is used in the prototype; real factories would usually use a historian, message broker, PostgreSQL, cloud platform, or plant data infrastructure.

## 15. How to Run

Create Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start API:

```bash
bash scripts/run_api.sh
```

Start C# collector in another terminal:

```bash
cd acquisition-csharp/SensorCollector
dotnet run
```

Build processed dataset:

```bash
cd ../..
python backend-python/src/data/preprocessing.py
```

Train all models:

```bash
python backend-python/src/models/train_all.py
```

Start dashboard:

```bash
bash scripts/run_dashboard.sh
```

## 16. Demo Flow

Recommended interview demo:

1. Open FastAPI `/health`.
2. Run C# collector and show console logs.
3. Open SQLite row counts with `/data-acquisition/status`.
4. Run preprocessing and show processed CSV.
5. Train models and show metrics JSON.
6. Call `/predict/failure`.
7. Open Streamlit dashboard.
8. Export Markdown report.
9. Explain limitations honestly.

## 17. Results

Expected generated outputs:

```text
data/processed/processed_ml_dataset.csv
models/failure_classifier.joblib
models/rul_regressor.joblib
models/anomaly_detector.joblib
models/failure_classifier_metrics.json
models/rul_regressor_metrics.json
models/anomaly_detector_metrics.json
reports/dashboard_report.md
```

Actual metric values depend on the simulated data volume and settings.

## 18. Limitations

- Simulated data only
- Simulated labels only
- RUL is heuristic and not validated on real machines
- SQLite is suitable for a local prototype, not high-volume factory deployment
- No PLC, OPC UA, MQTT, historian, or MES integration yet
- No authentication or role-based dashboard access yet
- No real factory acceptance testing
- Not a closed-loop control system

## 19. Future Work

- Add OPC UA or MQTT adapter
- Add Docker Compose for API and dashboard
- Add PostgreSQL option
- Add experiment tracking
- Add drift monitoring
- Add authentication
- Add unit and integration tests
- Add synthetic data replay mode
- Add CI workflow
- Add separate dashboard pages as modules

## 20. Portfolio Notes

Good interview positioning:

> I built this as a simulated-data working prototype to show the full industrial AI workflow from C# data acquisition through API ingestion, SQLite storage, Python ML training, inference endpoints, and a Streamlit operations dashboard. It does not use real Seagate data, but it is aligned with smart manufacturing tasks such as predictive maintenance, anomaly detection, and production-line monitoring.

## Run Full Demo

Run the complete Python core loop with one command:

```bash
bash scripts/run_full_demo.sh
```

The demo will:

1. check Python and dependencies;
2. optionally build the C# collector if .NET SDK is installed;
3. reset and initialize a SQLite demo database;
4. generate synthetic HDD / precision electronics smart manufacturing data;
5. run preprocessing and feature engineering;
6. run leakage checks;
7. train all models;
8. execute a prediction;
9. validate dashboard data availability;
10. generate `DEMO_VALIDATION.md` and `reports/demo_report.md`.

Expected summary:

```text
PASS: database initialized
PASS: synthetic factory data generated
PASS: preprocessing completed
PASS: feature engineering completed
PASS: leakage checks passed
PASS: models trained
PASS: prediction executed
PASS: dashboard data available
PASS: reports generated
```

## Synthetic Factory Data Generator

Generate data manually:

```bash
python scripts/generate_synthetic_factory_data.py \
  --start-date 2026-05-01T06:00:00 \
  --hours 168 \
  --interval-minutes 5 \
  --lines 4 \
  --machines-per-line 8 \
  --profile high_load_stress \
  --seed 42 \
  --output-db data/smart_factory.db \
  --output-csv-dir data/generated \
  --reset
```

The generator creates synthetic data only. It does not use real Seagate data, proprietary factory data, or real process parameters.

## Test Command

```bash
pytest -q
```

The test suite covers ingestion, repository setup, preprocessing, feature engineering, leakage checks, ML smoke training, and dashboard data helpers.

## Dashboard Screenshots

Screenshots must come from the actual Streamlit dashboard. Do not use fake screenshots.

Recommended flow:

```bash
bash scripts/run_full_demo.sh
bash scripts/run_dashboard.sh
python scripts/capture_dashboard_screenshots.py
```

If Playwright is unavailable, the screenshot script writes manual capture instructions to `assets/screenshots/MANUAL_SCREENSHOT_INSTRUCTIONS.md`.

Planned screenshot paths:

```text
assets/screenshots/01_executive_overview.png
assets/screenshots/02_data_acquisition.png
assets/screenshots/03_line_monitoring.png
assets/screenshots/04_equipment_health.png
assets/screenshots/05_anomaly_detection.png
assets/screenshots/06_data_quality.png
assets/screenshots/07_model_registry.png
assets/screenshots/08_reports.png
```

Example Markdown references after capturing real screenshots:

```markdown
![Executive Overview](assets/screenshots/01_executive_overview.png)
![Equipment Health](assets/screenshots/04_equipment_health.png)
![Model Registry](assets/screenshots/07_model_registry.png)
```

## Docker Run

Validate compose file:

```bash
docker compose config
```

Build and run:

```bash
docker compose build
docker compose up
```

API:

```text
http://127.0.0.1:8000
```

Dashboard:

```text
http://127.0.0.1:8501
```

## CI

GitHub Actions workflow is defined in:

```text
.github/workflows/ci.yml
```

CI runs Python compile checks, pytest, basic imports, and optional .NET restore/build when available.
