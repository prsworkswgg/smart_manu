# Smart Manufacturing AI Operations Platform

I built this project as a runnable smart manufacturing demo, not just a model
notebook. The goal is to show the full loop: collect machine data, store it,
clean it, train models, serve predictions, and give an operations team a
dashboard they could actually discuss.

The data is synthetic. No real factory data, proprietary process data, or
Seagate data is included.

## What It Does

The project connects several pieces that normally get separated in portfolio
projects:

```text
C# simulated data collector
-> FastAPI ingestion API
-> SQLite database
-> data quality checks
-> feature engineering
-> ML training
-> prediction endpoints
-> Streamlit dashboard
-> Markdown reports
```

It is meant to feel close to a real industrial AI workflow while staying honest
about what is simulated.

## Why I Built It

Many ML demos stop after training a model. This one goes further because real
manufacturing analytics work usually needs more than a notebook:

- data needs to arrive from another system;
- bad or missing records need to be handled;
- features need to be built from stored process history;
- models need to be saved and loaded again for inference;
- operators need a dashboard, not only a CSV file;
- the limits of the data need to be clear.

That is the main idea behind this repo.

## What Is Real Here

- The C# collector is a runnable .NET console app.
- The collector sends HTTP requests to the Python API.
- FastAPI validates and stores incoming readings.
- SQLite is used as the local system of record.
- Python preprocessing reads from the database and creates a training dataset.
- The ML scripts train and save model artifacts.
- Prediction endpoints load the saved artifacts.
- The Streamlit dashboard reads real outputs from the local database/files.
- GitHub Actions runs compile checks, pytest, import checks, and an optional
  .NET build.

## What Is Not Real Here

This is not a deployed production system.

- It uses simulated sensor and production-line data.
- Failure labels and RUL values are generated for demo purposes.
- It has not been validated against real machines.
- It does not connect to PLC, OPC UA, MQTT, MES, historian, or SCADA systems.
- SQLite is fine for a local prototype, not for high-volume factory history.
- There is no authentication, role-based access, or OT cybersecurity layer.
- It is not a closed-loop control system.

Any real factory deployment would need real sensor integration, process-owner
review, labeled maintenance history, IT/OT architecture review, cybersecurity
review, and factory acceptance testing.

## Main Components

### C# Data Collector

Location:

```text
acquisition-csharp/SensorCollector
```

The collector simulates machine sensor readings and production events. It uses
`HttpClient` to post records to the API, writes failed records to a local JSONL
buffer, and retries buffered records later.

Useful commands:

```bash
cd acquisition-csharp/SensorCollector
dotnet restore
dotnet build
dotnet run
```

### FastAPI Backend

Location:

```text
backend-python/api/main.py
```

Start the API:

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

### Data And ML Pipeline

The Python pipeline handles data quality, feature engineering, model training,
model loading, prediction helpers, health scoring, and diagnostic hints.

Run preprocessing:

```bash
python backend-python/src/data/preprocessing.py
```

Train all models:

```bash
python backend-python/src/models/train_all.py
```

Models currently include:

- failure classification;
- RUL regression;
- anomaly detection with IsolationForest.

### Streamlit Dashboard

Location:

```text
dashboard/app.py
```

Start the dashboard:

```bash
bash scripts/run_dashboard.sh
```

The dashboard includes:

- Executive Overview
- Data Acquisition Status
- Line Monitoring
- Equipment Health
- Process Anomaly
- Data Quality
- Model Training & Registry
- Reports / Edge Deployment

It is designed to keep working even when local tables are empty, which makes the
demo easier to start from a clean checkout.

## Quick Start

Python 3.10+ is recommended. The CI workflow uses Python 3.11.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the full Python demo loop:

```bash
bash scripts/run_full_demo.sh
```

That script will:

1. check Python and required packages;
2. build the C# collector if the .NET SDK is available;
3. create a local SQLite demo database;
4. generate synthetic factory data;
5. run preprocessing and feature engineering;
6. run leakage checks;
7. train the models;
8. validate prediction and dashboard data;
9. write demo reports.

Expected pass messages include:

```text
PASS: synthetic factory data generated
PASS: preprocessing completed
PASS: leakage checks passed
PASS: models trained
PASS: prediction executed
PASS: dashboard data available
PASS: full demo complete
```

## Manual Demo Flow

For an interview or walkthrough, I would usually show it in this order:

1. Start the API and open `/health`.
2. Run the C# collector and show records being posted.
3. Check `/data-acquisition/status`.
4. Run preprocessing and inspect the processed dataset.
5. Train the models and open the metrics JSON files.
6. Call one prediction endpoint.
7. Open the Streamlit dashboard.
8. Export or review the Markdown report.
9. Explain that the data and labels are simulated.

## Synthetic Data

You can generate a larger local dataset manually:

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

The simulated process includes values such as cycle time, throughput, yield,
rejects, rework, downtime, tool wear, vibration, current, torque, and process
stability.

## Generated Files

The repo keeps source code, tests, configs, docs, and placeholders. Local demo
outputs are regenerated when needed.

Common generated paths:

```text
data/processed/processed_ml_dataset.csv
models/failure_classifier.joblib
models/rul_regressor.joblib
models/anomaly_detector.joblib
models/failure_classifier_metrics.json
models/rul_regressor_metrics.json
models/anomaly_detector_metrics.json
reports/demo_report.md
```

Model files, local databases, and generated datasets are intentionally ignored
by git.

## Tests And CI

Run tests locally:

```bash
pytest -q
```

The test suite covers API ingestion, repository setup, preprocessing, feature
engineering, leakage checks, ML smoke training, and dashboard data helpers.

GitHub Actions is defined here:

```text
.github/workflows/ci.yml
```

CI runs:

- Python compile checks;
- `pytest -q`;
- basic import checks;
- optional .NET restore/build when `dotnet` is available.

## Docker

Validate the compose file:

```bash
docker compose config
```

Build and run:

```bash
docker compose build
docker compose up
```

Local URLs:

```text
API:       http://127.0.0.1:8000
Dashboard: http://127.0.0.1:8501
```

## Screenshots

Screenshots should come from the real Streamlit dashboard, not mock images.

Recommended flow:

```bash
bash scripts/run_full_demo.sh
bash scripts/run_dashboard.sh
python scripts/capture_dashboard_screenshots.py
```

If Playwright is not available, the screenshot script writes manual capture
instructions to:

```text
assets/screenshots/MANUAL_SCREENSHOT_INSTRUCTIONS.md
```

## Project Layout

```text
acquisition-csharp/   .NET collector and simulator
backend-python/       FastAPI app, data pipeline, ML code, tests
dashboard/            Streamlit dashboard
database/             SQLite schema
scripts/              demo, training, data generation, screenshot helpers
configs/              synthetic factory profiles
docs/                 design notes, runbooks, model card, limitations
assets/               diagrams and screenshot instructions
models/               generated model artifacts live here locally
reports/              generated demo reports live here locally
```

## Notes For Reviewers

The useful way to read this project is as a complete simulated workflow:

- C# shows how data could leave an edge collector.
- FastAPI and SQLite show ingestion and storage.
- Python shows the analytics pipeline.
- Streamlit shows how the output can be explained to operations users.

The project is intentionally honest about its boundary: it demonstrates the
engineering shape of a smart manufacturing AI system, but it does not claim real
factory validation.
