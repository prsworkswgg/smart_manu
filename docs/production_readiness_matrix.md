# Production Readiness Matrix

This matrix describes how close the project is to a real manufacturing operations platform and what must change before a real deployment.

| Area | Current MVP status | Production expectation | Gap / next step |
|---|---|---|---|
| Data source | C# collector and deterministic synthetic generator | PLC, OPC UA, MQTT, historian, MES, quality systems | Add real adapter layer and source authentication |
| Ingestion | FastAPI JSON endpoints with validation | Durable broker or historian-backed ingestion with schema governance | Add message broker, dead-letter queue, and idempotency strategy |
| Storage | SQLite local system of record | PostgreSQL, historian, lakehouse, or plant data platform | Add PostgreSQL profile and migrations |
| Data quality | Missing, duplicate, gap, impossible value, stuck sensor, dropout checks | Line-specific rules, calibration rules, sensor contracts, SLA alerts | Add configurable quality rules per line/station |
| Feature engineering | Historical rolling features and time-aware join | Versioned feature pipeline and reproducible training datasets | Add feature store or dataset versioning |
| ML training | Local scripts and joblib artifacts | Scheduled training, experiment tracking, model approval workflow | Add MLflow or registry approval gate |
| Inference | FastAPI loads artifacts and logs predictions | Scalable inference service with model version routing | Add model aliasing, canary deployment, and rollback |
| Observability | Request ID header, dashboard status, logs | Structured logs, metrics, traces, alerting | Add Prometheus/Grafana or cloud telemetry |
| Security | Local demo, no auth | SSO, RBAC, network segmentation, secrets management | Add authentication and role-based dashboard access |
| Dashboard | Streamlit command center with action queue | Operator UX with role-specific views and audit trail | Add acknowledgement workflow and work-order integration |
| Reports | CSV and Markdown exports | Shift reports, maintenance work orders, audit exports | Add persistent report history and PDF generation |
| Testing | 26 pytest checks covering core flow | Unit, integration, contract, load, E2E, security tests | Add API contract tests and dashboard smoke checks |
| Deployment | Docker Compose for API/dashboard | Hardened container deployment with health checks and backups | Add Compose health checks and deployment profiles |
| Validation | Synthetic metrics and demo validation | Factory acceptance testing with process-owner sign-off | Run pilot with real labels and maintenance records |

## MVP readiness rating

| Category | Rating | Notes |
|---|---:|---|
| Portfolio credibility | 9/10 | Strong end-to-end loop with honest limitations |
| Contractor implementation clarity | 8.5/10 | Clear files, scripts, tests, and architecture docs |
| Production architecture resemblance | 7.5/10 | Good boundaries; needs broker, auth, observability, and real data |
| Real factory deployability today | 4/10 | Not yet integrated with OT/IT, security, or real validation |

## Recommended next production hardening sprint

1. Add PostgreSQL with migrations while keeping SQLite as a demo profile.
2. Add API authentication and role-based dashboard access.
3. Add a message-broker adapter for MQTT or Kafka-style ingestion.
4. Add structured logging and service health checks.
5. Add model and data drift dashboard page.
6. Add an operator acknowledgement table for alerts.
7. Add real screenshot capture from the dashboard after demo generation.
