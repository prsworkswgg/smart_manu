"""Machine and line health scoring rules."""

from __future__ import annotations

from typing import Any


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Clamp a value to a bounded range."""
    return max(min_value, min(max_value, value))


def anomaly_risk_from_score(anomaly_score: float | None) -> float:
    """Convert IsolationForest score into risk-like value where 1 is high risk."""
    if anomaly_score is None:
        return 0.0
    # IsolationForest score_samples: lower/more negative is more anomalous.
    return clamp((-float(anomaly_score)) / 0.30)


def rul_penalty(rul_estimate_hours: float | None) -> float:
    """Convert RUL estimate into penalty."""
    if rul_estimate_hours is None:
        return 0.0
    rul = float(rul_estimate_hours)
    if rul <= 24:
        return 1.0
    if rul >= 168:
        return 0.0
    return clamp((168 - rul) / 144)


def compute_health_score(
    failure_probability: float | None,
    anomaly_score: float | None,
    tool_wear_index: float | None,
    process_drift_score: float | None,
    data_quality_penalty: float | None,
    rul_estimate_hours: float | None,
) -> dict[str, Any]:
    """Compute a 0-100 health score and risk level.

    Higher score is healthier.  Inputs are expected on 0-1 scales except RUL and
    anomaly score.
    """
    fp = clamp(float(failure_probability or 0.0))
    ar = anomaly_risk_from_score(anomaly_score)
    tw = clamp(float(tool_wear_index or 0.0))
    pd = clamp(float(process_drift_score or 0.0))
    dq = clamp(float(data_quality_penalty or 0.0))
    rp = rul_penalty(rul_estimate_hours)

    risk = clamp(0.34 * fp + 0.20 * ar + 0.16 * tw + 0.14 * pd + 0.08 * dq + 0.08 * rp)
    health = round(100.0 * (1.0 - risk), 2)

    if health >= 85:
        risk_level = "low"
        action = "Continue normal monitoring."
    elif health >= 70:
        risk_level = "medium"
        action = "Review trend and schedule inspection if degradation continues."
    elif health >= 50:
        risk_level = "high"
        action = "Plan maintenance inspection and check recent process changes."
    else:
        risk_level = "critical"
        action = "Escalate for immediate engineering review and possible controlled stop."

    return {
        "health_score": health,
        "risk_level": risk_level,
        "recommended_action": action,
        "risk_components": {
            "failure_probability": fp,
            "anomaly_risk": ar,
            "tool_wear_index": tw,
            "process_drift_score": pd,
            "data_quality_penalty": dq,
            "rul_penalty": rp,
            "combined_risk": risk,
        },
    }


def feature_based_scores(features: dict[str, Any]) -> dict[str, float]:
    """Extract score inputs from a feature dictionary."""
    tool_wear = float(features.get("tool_wear", 0.0) or 0.0)
    process_stability = float(features.get("process_stability_index", 1.0) or 1.0)
    temperature_delta = abs(float(features.get("temperature_delta", 0.0) or 0.0))
    flatline_flag = float(features.get("flatline_sensor_flag", 0.0) or 0.0)

    return {
        "tool_wear_index": clamp(tool_wear / 100.0),
        "process_drift_score": clamp((1.0 - process_stability) + temperature_delta / 80.0),
        "data_quality_penalty": clamp(flatline_flag),
    }
