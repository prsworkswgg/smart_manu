# Limitations

## Data limitations

This system uses simulated data only. It does not use real Seagate data, proprietary factory data, or validated production records.

## Model limitations

- Failure labels are simulated.
- RUL labels are heuristic.
- Anomaly detection is trained on simulated distributions.
- Metrics are useful for software validation, not real equipment validation.

## Deployment limitations

- SQLite is not intended for high-volume plant-wide deployment.
- No authentication is implemented.
- No OPC UA, MQTT, PLC, MES, historian, CMMS, or ERP integration is implemented.
- No safety interlock or closed-loop control exists.

## Operational limitations

Dashboard outputs should be interpreted as decision-support examples only. They are not certified maintenance instructions.

## Hiring honesty

The correct claim is:

> This is a Seagate-aligned simulated-data working prototype.

Do not claim:

- real Seagate production data
- real Seagate deployment
- factory-certified model
- validated predictive maintenance
- automatic process optimization
