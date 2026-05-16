# DEMO_VALIDATION

Timestamp: `2026-05-15T05:54:15.634088+00:00`

## PASS / FAIL Summary

- **PASS**: database initialized — `data/demo_smart_factory.db`
- **PASS**: synthetic factory data generated — `{"sensor_readings": 864, "production_events": 864, "synthetic_machine_sensor_readings": 864, "synthetic_production_events": 864, "synthetic_maintenance_events": 1, "synthetic_quality_events": 11, "synthetic_data_quality_events": 2, "data_quality_issues": 5, "model_training_runs": 3, "predictions": 0, "anomaly_alerts": 35}`
- **PASS**: preprocessing completed — `data/processed/demo_processed_ml_dataset.csv`
- **PASS**: feature engineering completed — `processed CSV exists`
- **PASS**: model artifact failure_classifier.joblib — `models/failure_classifier.joblib`
- **PASS**: model artifact rul_regressor.joblib — `models/rul_regressor.joblib`
- **PASS**: model artifact anomaly_detector.joblib — `models/anomaly_detector.joblib`
- **PASS**: metrics failure_classifier_metrics.json — `models/failure_classifier_metrics.json`
- **PASS**: metrics rul_regressor_metrics.json — `models/rul_regressor_metrics.json`
- **PASS**: metrics anomaly_detector_metrics.json — `models/anomaly_detector_metrics.json`
- **PASS**: prediction executed — `{"failure_probability": 1.8144873372968494e-05, "rul_estimate_hours": 1476.7603564111873, "anomaly_score": -0.4551869064443436, "health_score": 69.71, "risk_level": "high"}`
- **PASS**: dashboard data available — `sensor/prod rows exist`
- **PASS**: reports generated — `/Users/prswork/Desktop/smart-manufacturing-ai-operations-platform/reports/demo_report.md`

## Commands represented

```bash
python scripts/generate_synthetic_factory_data.py ...
python backend-python/src/data/preprocessing.py ...
python backend-python/src/models/train_all.py ...
python scripts/validate_demo_outputs.py ...
```

## Limitations

This demo uses synthetic data only. It does not use real Seagate data, proprietary factory data, or real factory deployment evidence.