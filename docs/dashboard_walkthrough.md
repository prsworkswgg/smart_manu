# Dashboard Walkthrough

## Executive Overview

Target user: manufacturing manager or hiring reviewer. Decision supported: understand current line risk, anomaly count, and average health.

Data sources: `sensor_readings`, `production_events`, `predictions`, `anomaly_alerts`.

## Data Acquisition Status

Target user: data engineer or manufacturing analyst. Decision supported: verify whether the collector/API/SQLite loop is receiving data.

Data sources: `sensor_readings`, `production_events`, `data_quality_issues`, `data_acquisition_logs`.

## Line Monitoring

Target user: line engineer. Decision supported: compare throughput, cycle time, yield, micro-stops, and downtime across stations.

Data source: `production_events`.

## Equipment Health

Target user: maintenance engineer. Decision supported: inspect machine health, failure probability, RUL, sensor trends, and recommended actions.

Data sources: `sensor_readings`, `predictions`.

## Process Anomaly

Target user: process engineer. Decision supported: identify affected line/station, anomaly score, alert messages, and diagnostic hints.

Data sources: `predictions`, `anomaly_alerts`, `diagnostic_hints`.

## Data Quality

Target user: data engineer / analyst. Decision supported: determine whether data is trustworthy enough for training and monitoring.

Data source: `data_quality_issues`.

## Model Training & Registry

Target user: ML engineer. Decision supported: inspect model versions, metrics, feature list, and artifact paths.

Data source: `model_training_runs`.

## Reports / Edge Deployment

Target user: reviewer or project owner. Decision supported: export evidence and understand edge deployment concept.

Data sources: `predictions`, `anomaly_alerts`, `data_quality_issues`.

## Limitations

Screenshots must come from actual dashboard pages reading SQLite/demo data. Do not use fake screenshots.
