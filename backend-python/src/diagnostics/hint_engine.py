"""Rule-based diagnostic hint engine."""

from __future__ import annotations

from typing import Any


def generate_diagnostic_hint(
    features: dict[str, Any],
    failure_probability: float | None = None,
    anomaly_score: float | None = None,
) -> dict[str, str]:
    """Generate diagnostic hint and recommended action from process signals."""
    vibration = float(features.get("vibration_rms", 0.0) or 0.0)
    motor_current = float(features.get("motor_current", 0.0) or 0.0)
    yield_drop = float(features.get("yield_drop_rate", 0.0) or 0.0)
    process_temp = float(features.get("process_temperature", 0.0) or 0.0)
    process_stability = float(features.get("process_stability_index", 1.0) or 1.0)
    torque = float(features.get("torque", 0.0) or 0.0)
    tool_wear = float(features.get("tool_wear", 0.0) or 0.0)
    flatline = bool(features.get("flatline_sensor_flag", False))

    if flatline:
        return {
            "diagnostic_hint": "Flatline sensor pattern detected. This may indicate a stuck sensor, not a healthy machine.",
            "recommended_action": "Check sensor wiring, PLC tag mapping, and acquisition logs before trusting the signal.",
        }

    if vibration >= 3.5 and motor_current >= 9.0 and yield_drop >= 0.01:
        return {
            "diagnostic_hint": "High vibration plus high motor current and yield drop suggests possible bearing wear, imbalance, or mechanical friction.",
            "recommended_action": "Inspect bearing condition, alignment, spindle balance, and recent reject trend.",
        }

    if process_temp >= 80.0 and process_stability <= 0.70:
        return {
            "diagnostic_hint": "High process temperature with low process stability suggests possible thermal process drift.",
            "recommended_action": "Review temperature control loop, cooling, recipe limits, and thermal chamber calibration.",
        }

    if torque >= 35.0 and tool_wear >= 70.0:
        return {
            "diagnostic_hint": "High torque with high tool wear suggests possible tool wear, overload, or increased mechanical resistance.",
            "recommended_action": "Inspect tooling, lubrication, material feed, and load profile.",
        }

    if failure_probability is not None and failure_probability >= 0.80:
        return {
            "diagnostic_hint": "Model indicates high failure probability based on combined equipment and process risk.",
            "recommended_action": "Escalate to maintenance engineering and compare with recent maintenance history.",
        }

    if anomaly_score is not None and anomaly_score < -0.15:
        return {
            "diagnostic_hint": "Process anomaly detector found a strong deviation from learned normal operating patterns.",
            "recommended_action": "Check recent process changes, raw material lots, sensor quality, and station setup.",
        }

    return {
        "diagnostic_hint": "No dominant rule-based fault signature detected. Continue monitoring trend and model outputs.",
        "recommended_action": "Monitor dashboard, review health score trend, and verify data quality.",
    }
