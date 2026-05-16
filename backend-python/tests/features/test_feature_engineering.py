from __future__ import annotations

import pandas as pd


def test_rolling_features_do_not_leak_future_values():
    from features.feature_engineering import add_engineered_features
    rows = []
    for i, vib in enumerate([1.0, 2.0, 100.0]):
        rows.append({
            "machine_id": "M1", "line_id": "L1", "station_id": "S1", "timestamp": f"2026-05-01T00:{i:02d}:00Z",
            "air_temperature": 25, "process_temperature": 50+i, "vibration_rms": vib, "vibration_peak": vib*3,
            "pressure": 100, "torque": 10, "rotational_speed": 1000, "motor_current": 5, "power_consumption": 2,
            "tool_wear": 10+i, "operating_hours": i, "production_load": .9, "ambient_humidity": 50,
            "cycle_time_sec": 5, "throughput_count": 10, "target_throughput": 12, "station_yield": .98,
            "reject_count": 0, "rework_count": 0, "defect_rate": .02, "micro_stop_count": 0, "downtime_minutes": 0,
            "wip_count": 10, "queue_length": 2, "inspection_score_proxy": .95, "process_stability_index": .9,
            "join_lag_seconds": 0
        })
    df = add_engineered_features(pd.DataFrame(rows), rolling_window=2)
    assert df.loc[1, "rolling_vibration_mean"] == 1.0
    assert df.loc[1, "rolling_vibration_mean"] != 100.0


def test_feature_dataframe_has_no_inf_values():
    from features.feature_engineering import add_engineered_features, FEATURE_COLUMNS
    df = pd.DataFrame([{"machine_id":"M","line_id":"L","station_id":"S","timestamp":"2026-05-01T00:00:00Z"}])
    out = add_engineered_features(df)
    assert not out[FEATURE_COLUMNS].isin([float("inf"), float("-inf")]).any().any()


def test_target_columns_are_not_training_features():
    from features.feature_engineering import FEATURE_COLUMNS, TARGET_COLUMNS
    assert not set(FEATURE_COLUMNS).intersection(TARGET_COLUMNS)


def test_leakage_checker_blocks_bad_features():
    from features.feature_engineering import assert_no_leakage
    try:
        assert_no_leakage(["vibration_rms", "failure_label"])
    except ValueError:
        return
    raise AssertionError("leakage checker did not block failure_label")


def test_no_hidden_degradation_in_features():
    from features.feature_engineering import FEATURE_COLUMNS
    assert "hidden_degradation_state" not in FEATURE_COLUMNS
