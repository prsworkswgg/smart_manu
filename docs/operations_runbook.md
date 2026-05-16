# Operations Runbook

This runbook is written for a local demo or contractor handoff. The system uses simulated data only.

## 1. Start API

```bash
bash scripts/run_api.sh
```

Check:

```bash
curl -i http://127.0.0.1:8000/health
```

Expected:

```text
HTTP/1.1 200 OK
x-request-id: <request-id>
```

Response body includes:

```json
{
  "status": "ok",
  "service": "smart-manufacturing-ai-operations-platform",
  "data_policy": "simulated_data_only"
}
```

## 2. Start C# collector

```bash
cd acquisition-csharp/SensorCollector
dotnet run
```

Expected behavior:

- collector sends sensor readings and production events;
- failed HTTP calls are written to local JSONL buffer;
- retry queue replays buffered records when API becomes available.

## 3. Check ingestion

```bash
curl http://127.0.0.1:8000/data-acquisition/status
```

Dashboard location:

```text
Data Acquisition Status
```

Operator interpretation:

- **Live stream active** means latest records are recent.
- **Stream delayed** means data exists but freshness is outside the live target.
- **Replay / offline dataset** means data is available for demo analysis but not a live stream.

## 4. Run preprocessing

```bash
python backend-python/src/data/preprocessing.py
```

This step:

- joins sensor and production records using historical timestamps only;
- runs data-quality checks;
- writes processed ML dataset.

## 5. Train models

```bash
python backend-python/src/models/train_all.py
```

Artifacts:

```text
models/failure_classifier.joblib
models/rul_regressor.joblib
models/anomaly_detector.joblib
models/*_metrics.json
```

Dashboard location:

```text
Model Training & Registry
```

## 6. Start dashboard

```bash
bash scripts/run_dashboard.sh
```

Open:

```text
http://127.0.0.1:8501
```

Recommended walkthrough:

1. Executive Overview — explain operating posture and action queue.
2. Data Acquisition Status — prove data is not hardcoded.
3. Line Monitoring — show production KPIs.
4. Equipment Health — show one machine's trend and recommendation.
5. Process Anomaly — show anomaly score or empty-state behavior.
6. Data Quality — explain guardrails before trusting ML.
7. Model Training & Registry — show artifacts, metrics, and features.
8. Reports / Edge Deployment — export handover report.

## Common incidents

### API is down

Symptom:

```text
C# collector buffers JSONL records
```

Action:

```bash
curl -i http://127.0.0.1:8000/health
bash scripts/run_api.sh
```

### Dashboard points to the wrong database

Symptom:

```text
Dashboard opens but tables are empty.
```

Action:

1. Check SQLite path in dashboard sidebar.
2. Check `SMOP_DB_PATH`.
3. Re-run the same command with explicit database path if needed.

```bash
export SMOP_DB_PATH=database/smart_manufacturing.db
bash scripts/run_dashboard.sh
```

### Processed dataset has zero rows

Likely causes:

- no sensor data;
- no production data;
- line/station mismatch;
- timestamps outside join tolerance.

Action:

```bash
python backend-python/src/data/preprocessing.py --join-tolerance-minutes 30
```

### Prediction endpoint returns HTTP 409

Symptom:

```text
Model artifact is missing or not trained.
```

Action:

```bash
python backend-python/src/models/train_all.py
```

### Action queue shows data-quality warnings

Interpretation:

The model may be technically available, but the input stream should be reviewed first.

Action:

1. Open Data Quality page.
2. Identify affected line/station/machine.
3. Check duplicate timestamps, gaps, stuck sensors, and impossible values.
4. Re-run preprocessing after fixing or regenerating data.

## Incident debug template

```text
Timestamp:
Command:
Layer:
Request ID:
Database path:
Observed behavior:
Expected behavior:
Relevant file:
Recent change:
```

Layer options:

- C# acquisition
- FastAPI
- SQLite
- Data quality
- Feature engineering
- ML training
- Inference
- Streamlit dashboard
- Docker / environment

## Production rollout note

Before using this design in a real factory, add authentication, network segmentation, real sensor integration, historian or message broker integration, structured logging, monitoring, backup/restore, and factory acceptance testing.
