"""FastAPI backend for ingestion and model inference."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

# Add backend-python/src to sys.path for direct uvicorn execution.
BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository
from models.model_loader import ModelNotTrainedError
from models.predict import run_full_prediction


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize local system-of-record on service startup."""
    repository.initialize_database()
    yield


app = FastAPI(
    title="Smart Manufacturing AI Operations Platform API",
    version="0.7.0",
    description=(
        "Simulated-data FastAPI backend for smart manufacturing ingestion, "
        "batch loading, model inference, and operations telemetry."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service health and operational metadata."},
        {"name": "ingestion", "description": "Sensor and production event ingestion endpoints."},
        {"name": "inference", "description": "Failure, RUL, anomaly, and health-score predictions."},
        {"name": "operations", "description": "Dashboard support endpoints for registry and line health."},
    ],
)


@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    """Attach a request ID to every response for operator-facing troubleshooting."""
    request_id = request.headers.get("x-request-id", str(uuid4()))
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


class SensorReadingPayload(BaseModel):
    """Sensor reading contract sent by the C# collector."""

    event_id: str | None = None
    machine_id: str
    line_id: str
    station_id: str
    timestamp: datetime
    air_temperature: float | None = None
    process_temperature: float | None = None
    vibration_rms: float | None = None
    vibration_peak: float | None = None
    pressure: float | None = None
    torque: float | None = None
    rotational_speed: float | None = None
    motor_current: float | None = None
    power_consumption: float | None = None
    tool_wear: float | None = None
    operating_hours: float | None = None
    production_load: float | None = None
    ambient_humidity: float | None = None


class ProductionEventPayload(BaseModel):
    """Production event contract sent by the C# collector."""

    event_id: str | None = None
    line_id: str
    station_id: str
    batch_id: str | None = None
    shift: str | None = None
    timestamp: datetime
    cycle_time_sec: float | None = None
    throughput_count: int | None = None
    target_throughput: int | None = None
    station_yield: float | None = None
    reject_count: int | None = None
    rework_count: int | None = None
    defect_rate: float | None = None
    micro_stop_count: int | None = None
    downtime_minutes: float | None = None
    wip_count: int | None = None
    queue_length: int | None = None
    inspection_score_proxy: float | None = None
    process_stability_index: float | None = None
    operator_group: str | None = None


class BatchPayload(BaseModel):
    """Batch ingestion payload."""

    sensor_readings: list[SensorReadingPayload] = Field(default_factory=list)
    production_events: list[ProductionEventPayload] = Field(default_factory=list)


class InferencePayload(BaseModel):
    """Flexible inference payload.

    The model accepts all ingestion fields plus engineered fields if provided.
    Extra fields are allowed so later feature additions do not break clients.
    """

    model_config = ConfigDict(extra="allow")

    machine_id: str
    line_id: str
    station_id: str
    timestamp: datetime | None = None

    air_temperature: float | None = None
    process_temperature: float | None = None
    vibration_rms: float | None = None
    vibration_peak: float | None = None
    pressure: float | None = None
    torque: float | None = None
    rotational_speed: float | None = None
    motor_current: float | None = None
    power_consumption: float | None = None
    tool_wear: float | None = None
    operating_hours: float | None = None
    production_load: float | None = None
    ambient_humidity: float | None = None

    cycle_time_sec: float | None = None
    throughput_count: int | None = None
    target_throughput: int | None = None
    station_yield: float | None = None
    reject_count: int | None = None
    rework_count: int | None = None
    defect_rate: float | None = None
    micro_stop_count: int | None = None
    downtime_minutes: float | None = None
    wip_count: int | None = None
    queue_length: int | None = None
    inspection_score_proxy: float | None = None
    process_stability_index: float | None = None


@app.get("/health", tags=["health"])
def health() -> dict[str, Any]:
    """API health endpoint for the C# collector."""
    return {
        "status": "ok",
        "service": "smart-manufacturing-ai-operations-platform",
        "data_policy": "simulated_data_only",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/ingest/sensor-reading", tags=["ingestion"])
def ingest_sensor_reading(payload: SensorReadingPayload) -> dict[str, Any]:
    """Ingest one sensor reading into SQLite."""
    row = payload.model_dump()
    row["timestamp"] = row["timestamp"].isoformat()
    row_id = repository.insert_sensor_reading(row)
    return {"status": "inserted", "table": "sensor_readings", "id": row_id}


@app.post("/ingest/production-event", tags=["ingestion"])
def ingest_production_event(payload: ProductionEventPayload) -> dict[str, Any]:
    """Ingest one production event into SQLite."""
    row = payload.model_dump()
    row["timestamp"] = row["timestamp"].isoformat()
    row_id = repository.insert_production_event(row)
    return {"status": "inserted", "table": "production_events", "id": row_id}


@app.post("/ingest/batch", tags=["ingestion"])
def ingest_batch(payload: BatchPayload) -> dict[str, Any]:
    """Ingest a batch of sensor readings and production events."""
    sensor_ids = []
    production_ids = []
    for sensor in payload.sensor_readings:
        row = sensor.model_dump()
        row["timestamp"] = row["timestamp"].isoformat()
        sensor_ids.append(repository.insert_sensor_reading(row))
    for event in payload.production_events:
        row = event.model_dump()
        row["timestamp"] = row["timestamp"].isoformat()
        production_ids.append(repository.insert_production_event(row))
    return {
        "status": "inserted",
        "sensor_count": len(sensor_ids),
        "production_count": len(production_ids),
        "sensor_ids": sensor_ids,
        "production_ids": production_ids,
    }


@app.get("/data-acquisition/status", tags=["operations"])
def data_acquisition_status() -> dict[str, Any]:
    """Return ingestion row counts and latest timestamps."""
    return repository.get_data_acquisition_status()


def _payload_dict(payload: InferencePayload) -> dict[str, Any]:
    row = payload.model_dump()
    if row.get("timestamp") is None:
        row["timestamp"] = datetime.now(timezone.utc).isoformat()
    elif hasattr(row["timestamp"], "isoformat"):
        row["timestamp"] = row["timestamp"].isoformat()
    return row


def _predict_and_log(payload: InferencePayload, endpoint_name: str) -> dict[str, Any]:
    try:
        row = _payload_dict(payload)
        result = run_full_prediction(row)

        response = {
            "failure_probability": result["failure_probability"],
            "rul_estimate_hours": result["rul_estimate_hours"],
            "anomaly_score": result["anomaly_score"],
            "anomaly_flag": result["anomaly_flag"],
            "health_score": result["health_score"],
            "risk_level": result["risk_level"],
            "recommended_action": result["recommended_action"],
            "diagnostic_hint": result["diagnostic_hint"],
            "model_version": result["model_version"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint_name,
        }

        repository.insert_prediction(
            {
                "machine_id": row.get("machine_id"),
                "line_id": row.get("line_id"),
                "station_id": row.get("station_id"),
                "timestamp": row.get("timestamp"),
                "failure_probability": result["failure_probability"],
                "rul_estimate_hours": result["rul_estimate_hours"],
                "anomaly_score": result["anomaly_score"],
                "anomaly_flag": result["anomaly_flag"],
                "health_score": result["health_score"],
                "risk_level": result["risk_level"],
                "recommended_action": result["recommended_action"],
                "diagnostic_hint": result["diagnostic_hint"],
                "model_version": json.dumps(result["model_version"], ensure_ascii=False),
                "payload_json": json.dumps(row, ensure_ascii=False),
            }
        )

        if result["risk_level"] in {"high", "critical"} or int(result["anomaly_flag"]) == 1:
            repository.insert_anomaly_alert(
                {
                    "machine_id": row.get("machine_id"),
                    "line_id": row.get("line_id"),
                    "station_id": row.get("station_id"),
                    "timestamp": row.get("timestamp"),
                    "anomaly_score": result["anomaly_score"],
                    "severity": result["risk_level"],
                    "message": result["diagnostic_hint"],
                    "source": endpoint_name,
                }
            )

        repository.insert_diagnostic_hint(
            {
                "machine_id": row.get("machine_id"),
                "line_id": row.get("line_id"),
                "station_id": row.get("station_id"),
                "timestamp": row.get("timestamp"),
                "hint": result["diagnostic_hint"],
                "recommended_action": result["recommended_action"],
            }
        )

        return response
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc


@app.post("/predict/failure", tags=["inference"])
def predict_failure_endpoint(payload: InferencePayload) -> dict[str, Any]:
    """Predict failure probability plus health context."""
    return _predict_and_log(payload, "predict_failure")


@app.post("/predict/rul", tags=["inference"])
def predict_rul_endpoint(payload: InferencePayload) -> dict[str, Any]:
    """Predict RUL plus health context."""
    return _predict_and_log(payload, "predict_rul")


@app.post("/detect/anomaly", tags=["inference"])
def detect_anomaly_endpoint(payload: InferencePayload) -> dict[str, Any]:
    """Detect process anomaly plus health context."""
    return _predict_and_log(payload, "detect_anomaly")


@app.get("/model-runs", tags=["operations"])
def model_runs(limit: int = 50) -> list[dict[str, Any]]:
    """Return model training run history."""
    return repository.list_model_runs(limit=limit)


@app.get("/predictions", tags=["operations"])
def predictions(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent predictions."""
    return repository.list_predictions(limit=limit)


@app.get("/alerts", tags=["operations"])
def alerts(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent anomaly alerts."""
    return repository.list_alerts(limit=limit)


@app.get("/line-health/{line_id}", tags=["operations"])
def line_health(line_id: str) -> dict[str, Any]:
    """Return aggregate health for a line."""
    return repository.get_line_health(line_id)
