#!/usr/bin/env python3
"""Generate synthetic HDD / precision electronics smart manufacturing data.

Positioning:
Synthetic HDD / Precision Electronics Smart Manufacturing Dataset inspired by
public high-level information about manufacturing operations in Thailand.  No
real Seagate data.  No proprietary data.  No real factory deployment.

The generator writes rich synthetic tables and also maps rows into the existing
``sensor_readings`` and ``production_events`` tables so the current preprocessing,
ML, and dashboard pipeline continues to work.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1] / "backend-python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository

SITES = ["TH_PRECISION_SITE_A", "TH_COMPONENT_SITE_B"]
AREAS = [
    "AREA_01_SLIDER_PROCESSING",
    "AREA_02_HEAD_ASSEMBLY",
    "AREA_03_HGA_ASSEMBLY",
    "AREA_04_DRIVE_ASSEMBLY",
    "AREA_05_FINAL_TEST",
    "AREA_06_REWORK_INSPECTION",
    "AREA_07_PACKAGING",
]
PRODUCT_FAMILIES = ["HDD_COMPONENT_ALPHA", "HDD_COMPONENT_BETA", "PRECISION_ASSEMBLY_GAMMA"]
RECIPES = ["RCP_STD_A", "RCP_STD_B", "RCP_HIGH_PRECISION", "RCP_FINAL_TEST"]
FAILURE_MODES = [
    "NORMAL",
    "TOOL_WEAR_DEGRADATION",
    "ALIGNMENT_DRIFT",
    "VACUUM_INSTABILITY",
    "MOTOR_BEARING_STRESS",
    "THERMAL_INSTABILITY",
    "AIR_PRESSURE_DROP",
    "SENSOR_DROPOUT",
    "POST_MAINTENANCE_RECOVERY",
]
DQ_ISSUES = [
    "MISSING_VALUE",
    "DUPLICATE_EVENT",
    "TIMESTAMP_GAP",
    "OUT_OF_ORDER_EVENT",
    "STUCK_SENSOR",
    "SENSOR_DROPOUT",
    "IMPOSSIBLE_VALUE",
    "DELAYED_MESSAGE",
    "CLOCK_SKEW",
    "NEGATIVE_CYCLE_TIME",
    "ZERO_THROUGHPUT_WHILE_RUNNING",
]
PROFILES = {
    "normal_operation": {"load": 0.80, "degrade": 0.75, "quality": 0.70, "dq": 0.70, "shock": 0.70},
    "early_degradation": {"load": 0.90, "degrade": 1.20, "quality": 0.90, "dq": 0.80, "shock": 0.90},
    "unstable_process": {"load": 1.00, "degrade": 1.00, "quality": 1.55, "dq": 1.10, "shock": 1.20},
    "quality_excursion": {"load": 1.00, "degrade": 1.00, "quality": 2.20, "dq": 1.00, "shock": 1.00},
    "post_maintenance_recovery": {"load": 0.75, "degrade": 0.65, "quality": 0.90, "dq": 0.90, "shock": 0.80},
    "high_load_stress": {"load": 1.22, "degrade": 1.45, "quality": 1.25, "dq": 1.10, "shock": 1.40},
    "data_quality_incident": {"load": 0.95, "degrade": 0.95, "quality": 0.95, "dq": 3.50, "shock": 1.00},
}


@dataclass
class MachineState:
    site_id: str
    area_id: str
    line_id: str
    machine_id: str
    station_id: str
    machine_age_days: float
    base_cycle: float
    base_torque: float
    base_temp: float
    target_throughput: int
    variation: float
    degradation: float
    hours_since_maintenance: float
    post_maintenance_steps: int = 0
    process_drift: float = 0.0
    quality_excursion_remaining: int = 0
    shock_remaining: int = 0
    stuck_sensor_remaining: int = 0
    last_vibration: float | None = None


def parse_start(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def shift_for_time(ts: datetime) -> str:
    hour = ts.hour
    if 6 <= hour < 14:
        return "DAY"
    if 14 <= hour < 22:
        return "EVENING"
    return "NIGHT"


def load_state_for_profile(profile: str, rng: random.Random) -> str:
    if profile == "high_load_stress":
        return rng.choices(["NORMAL_LOAD", "HIGH_LOAD", "LOW_LOAD"], [0.42, 0.54, 0.04])[0]
    if profile == "normal_operation":
        return rng.choices(["NORMAL_LOAD", "LOW_LOAD", "HIGH_LOAD"], [0.72, 0.18, 0.10])[0]
    return rng.choices(["NORMAL_LOAD", "HIGH_LOAD", "LOW_LOAD"], [0.58, 0.30, 0.12])[0]


def load_multiplier(load_state: str) -> float:
    return {"LOW_LOAD": 0.82, "NORMAL_LOAD": 1.0, "HIGH_LOAD": 1.18}[load_state]


def shift_multiplier(shift: str) -> float:
    return {"DAY": 1.00, "EVENING": 1.03, "NIGHT": 1.07}[shift]


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def create_machines(lines: int, machines_per_line: int, rng: random.Random) -> list[MachineState]:
    machines: list[MachineState] = []
    for line_idx in range(1, lines + 1):
        site_id = SITES[(line_idx - 1) % len(SITES)]
        area_id = AREAS[(line_idx - 1) % len(AREAS)]
        line_id = f"{site_id}_LINE_{line_idx:02d}"
        for machine_idx in range(1, machines_per_line + 1):
            area_short = area_id.split("_", 2)[-1][:10]
            machine_id = f"{line_id}_M{machine_idx:02d}"
            station_id = f"{line_id}_ST{machine_idx:02d}"
            variation = rng.normalvariate(1.0, 0.06)
            machines.append(
                MachineState(
                    site_id=site_id,
                    area_id=area_id,
                    line_id=line_id,
                    machine_id=machine_id,
                    station_id=station_id,
                    machine_age_days=rng.uniform(120, 1800),
                    base_cycle=rng.uniform(4.2, 9.5) * variation,
                    base_torque=rng.uniform(12, 32) * variation,
                    base_temp=rng.uniform(42, 68),
                    target_throughput=rng.randint(8, 18),
                    variation=variation,
                    degradation=rng.uniform(0.05, 0.32),
                    hours_since_maintenance=rng.uniform(12, 420),
                )
            )
    return machines


def choose_failure_mode(state: MachineState, pressure: float, temp: float, rng: random.Random) -> str:
    if state.post_maintenance_steps > 0:
        return "POST_MAINTENANCE_RECOVERY"
    if state.stuck_sensor_remaining > 0:
        return "SENSOR_DROPOUT"
    if pressure < 92:
        return "AIR_PRESSURE_DROP"
    if temp > state.base_temp + 20:
        return "THERMAL_INSTABILITY"
    if state.degradation > 0.82:
        return rng.choices(["TOOL_WEAR_DEGRADATION", "MOTOR_BEARING_STRESS", "ALIGNMENT_DRIFT"], [0.45, 0.35, 0.20])[0]
    if state.degradation > 0.60:
        return rng.choices(["NORMAL", "TOOL_WEAR_DEGRADATION", "ALIGNMENT_DRIFT", "VACUUM_INSTABILITY"], [0.42, 0.25, 0.20, 0.13])[0]
    return "NORMAL"


def maybe_start_burst(state: MachineState, profile: str, rng: random.Random) -> None:
    profile_cfg = PROFILES[profile]
    if state.quality_excursion_remaining <= 0 and rng.random() < 0.0025 * profile_cfg["quality"]:
        state.quality_excursion_remaining = rng.randint(6, 30)
    if state.shock_remaining <= 0 and rng.random() < 0.0018 * profile_cfg["shock"]:
        state.shock_remaining = rng.randint(2, 8)
    if state.stuck_sensor_remaining <= 0 and rng.random() < 0.0009 * profile_cfg["dq"]:
        state.stuck_sensor_remaining = rng.randint(4, 14)


def maybe_maintenance(state: MachineState, ts: datetime, rng: random.Random) -> dict[str, Any] | None:
    probability = 0.0008 + (0.006 if state.degradation > 0.86 else 0) + (0.002 if state.hours_since_maintenance > 350 else 0)
    if rng.random() >= probability:
        return None
    before = state.degradation
    reset_ratio = rng.uniform(0.25, 0.55)
    state.degradation *= reset_ratio
    state.hours_since_maintenance = 0.0
    state.process_drift *= 0.35
    state.post_maintenance_steps = rng.randint(8, 24)
    return {
        "event_id": f"MAINT_{state.machine_id}_{int(ts.timestamp())}",
        "site_id": state.site_id,
        "area_id": state.area_id,
        "line_id": state.line_id,
        "machine_id": state.machine_id,
        "station_id": state.station_id,
        "timestamp": ts.isoformat(),
        "maintenance_type": rng.choice(["PLANNED_PM", "TOOL_CHANGE", "ADJUSTMENT", "RECOVERY_CHECK"]),
        "reset_ratio": round(reset_ratio, 4),
        "degradation_before": round(before, 5),
        "degradation_after": round(state.degradation, 5),
        "duration_minutes": round(rng.uniform(20, 95), 2),
    }


def generate(args: argparse.Namespace) -> dict[str, Any]:
    rng = random.Random(args.seed)
    start = parse_start(args.start_date)
    profile = args.profile
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile}. Valid: {sorted(PROFILES)}")
    cfg = PROFILES[profile]
    steps = int((args.hours * 60) / args.interval_minutes)
    machines = create_machines(args.lines, args.machines_per_line, rng)

    sensor_rows: list[dict[str, Any]] = []
    production_rows: list[dict[str, Any]] = []
    maintenance_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    dq_rows: list[dict[str, Any]] = []

    for step in range(steps):
        ts = start + timedelta(minutes=step * args.interval_minutes)
        shift = shift_for_time(ts)
        day_curve = math.sin((ts.hour + ts.minute / 60) / 24 * math.pi * 2)
        ambient_temp = 27.5 + 3.0 * max(0, day_curve) + rng.normalvariate(0, 0.7)
        ambient_humidity = clamp(58 + rng.normalvariate(0, 7) - day_curve * 4, 35, 82)
        cleanroom_particle_proxy = max(0.02, rng.lognormvariate(-2.5, 0.35) * (1.0 + 0.15 * (shift == "NIGHT")))

        for state in machines:
            maybe_start_burst(state, profile, rng)
            maint = maybe_maintenance(state, ts, rng)
            if maint:
                maintenance_rows.append(maint)

            load_state = load_state_for_profile(profile, rng)
            load_mult = load_multiplier(load_state) * cfg["load"]
            shift_mult = shift_multiplier(shift)
            hours_delta = args.interval_minutes / 60.0
            state.hours_since_maintenance += hours_delta
            age_factor = 1.0 + min(state.machine_age_days / 2400.0, 0.85)
            degrade_inc = 0.0007 * hours_delta * load_mult * shift_mult * age_factor * cfg["degrade"]
            if state.shock_remaining > 0:
                degrade_inc += rng.uniform(0.003, 0.009)
                state.shock_remaining -= 1
            if state.post_maintenance_steps > 0:
                degrade_inc *= 0.55
                state.post_maintenance_steps -= 1
            state.degradation = clamp(state.degradation + degrade_inc, 0, 1.25)
            state.process_drift += rng.normalvariate(0.0005 * cfg["quality"], 0.002)
            if state.quality_excursion_remaining > 0:
                state.process_drift += rng.uniform(0.004, 0.012)
                state.quality_excursion_remaining -= 1

            pressure = 116 + rng.normalvariate(0, 4) - (12 if rng.random() < 0.006 * cfg["shock"] else 0)
            tool_wear = clamp(state.degradation * 100 + rng.normalvariate(0, 1.5), 0, 100)
            vibration = 0.55 + state.degradation * 4.2 + max(0, load_mult - 1.0) * 0.7 + rng.normalvariate(0, 0.12)
            if state.stuck_sensor_remaining > 0 and state.last_vibration is not None:
                vibration = state.last_vibration
                state.stuck_sensor_remaining -= 1
            else:
                state.last_vibration = vibration
            vibration = max(0.01, vibration)
            torque = state.base_torque + tool_wear * 0.23 + load_mult * 5.0 + rng.normalvariate(0, 1.1)
            motor_current = 3.0 + torque * 0.16 + vibration * 0.55 + rng.normalvariate(0, 0.25)
            process_temp = state.base_temp + ambient_temp * 0.08 + tool_wear * 0.13 + state.process_drift * 12 + load_mult * 2.5 + rng.normalvariate(0, 0.9)
            rotational_speed = max(200, 2200 + rng.normalvariate(0, 120) - tool_wear * 2.0)
            power = motor_current * 0.22 * rng.uniform(0.94, 1.08)
            failure_mode = choose_failure_mode(state, pressure, process_temp, rng)
            product_family = PRODUCT_FAMILIES[(step + hash(state.line_id)) % len(PRODUCT_FAMILIES)]
            recipe_id = RECIPES[(step // max(1, int(60 / args.interval_minutes)) + hash(state.machine_id)) % len(RECIPES)]
            lot_id = f"LOT_{state.site_id[-1]}_{ts.strftime('%Y%m%d')}_{(step // 12) % 999:03d}"
            event_id = f"SEN_{state.machine_id}_{step:06d}"

            sensor = {
                "event_id": event_id,
                "site_id": state.site_id,
                "area_id": state.area_id,
                "line_id": state.line_id,
                "machine_id": state.machine_id,
                "station_id": state.station_id,
                "timestamp": ts.isoformat(),
                "shift": shift,
                "load_state": load_state,
                "product_family": product_family,
                "recipe_id": recipe_id,
                "lot_id": lot_id,
                "failure_mode": failure_mode,
                "ambient_temperature": round(ambient_temp, 3),
                "ambient_humidity": round(ambient_humidity, 3),
                "cleanroom_particle_proxy": round(cleanroom_particle_proxy, 5),
                "machine_age_days": round(state.machine_age_days, 2),
                "hours_since_maintenance": round(state.hours_since_maintenance, 3),
                "hidden_degradation_state": round(state.degradation, 6),
                "tool_wear": round(tool_wear, 4),
                "air_temperature": round(ambient_temp, 3),
                "process_temperature": round(process_temp, 3),
                "vibration_rms": round(vibration, 5),
                "vibration_peak": round(vibration * rng.uniform(2.1, 3.7), 5),
                "pressure": round(pressure, 3),
                "torque": round(torque, 4),
                "rotational_speed": round(rotational_speed, 3),
                "motor_current": round(motor_current, 4),
                "power_consumption": round(power, 4),
                "production_load": round(load_mult, 4),
            }

            risk = clamp(0.42 * state.degradation + 0.15 * max(0, vibration - 2.0) / 4 + 0.10 * max(0, process_temp - state.base_temp) / 25 + 0.08 * (load_state == "HIGH_LOAD"), 0, 1)
            cycle = state.base_cycle * (1 + 0.36 * state.degradation + 0.05 * (shift == "NIGHT") + 0.20 * (load_state == "HIGH_LOAD")) + rng.normalvariate(0, 0.22)
            if failure_mode == "POST_MAINTENANCE_RECOVERY":
                cycle *= 1.03
            micro_stops = max(0, int(rng.poisson(lam=1) if hasattr(rng, 'poisson') else round(rng.expovariate(1 / (1 + 7 * risk)))))
            if state.shock_remaining > 0:
                micro_stops += rng.randint(1, 4)
            downtime = micro_stops * rng.uniform(0.08, 0.55)
            if rng.random() < 0.0025 * cfg["shock"]:
                downtime += rng.uniform(5, 24)
            target = state.target_throughput
            throughput = max(0, int(round(target * (state.base_cycle / max(cycle, 0.1)) * rng.uniform(0.88, 1.03) - downtime * 0.25)))
            if load_state == "LOW_LOAD":
                throughput = int(throughput * 0.80)
            base_defect = 0.004 + risk * 0.085 + max(0, state.process_drift) * 0.22 + cleanroom_particle_proxy * 0.10
            if state.quality_excursion_remaining > 0:
                base_defect += rng.uniform(0.025, 0.09) * cfg["quality"]
            defect_rate = clamp(base_defect + rng.normalvariate(0, 0.005), 0.0005, 0.35)
            first_pass_yield = clamp(1 - defect_rate - micro_stops * 0.0015, 0.55, 0.999)
            station_yield = clamp(first_pass_yield + rng.uniform(-0.008, 0.010), 0.50, 0.999)
            rejects = int(round(throughput * defect_rate))
            rework = int(round(rejects * rng.uniform(0.2, 0.7)))
            wip = max(0, int(round(throughput * rng.uniform(1.1, 4.2) + micro_stops * 5 + downtime)))
            queue = max(0, int(round(wip * rng.uniform(0.08, 0.45) + max(0, target - throughput) * rng.uniform(0.5, 1.5))))
            process_stability = clamp(1 - risk * 0.45 - max(0, state.process_drift) * 0.6 - micro_stops * 0.008, 0.30, 0.999)
            future_failure = int(risk > 0.72 or state.degradation > 0.90)
            rul_target = max(0.0, (0.96 - state.degradation) / max(degrade_inc / max(hours_delta, 1e-6), 1e-5))

            prod = {
                "event_id": f"PROD_{state.machine_id}_{step:06d}",
                "site_id": state.site_id,
                "area_id": state.area_id,
                "line_id": state.line_id,
                "machine_id": state.machine_id,
                "station_id": state.station_id,
                "timestamp": ts.isoformat(),
                "shift": shift,
                "load_state": load_state,
                "product_family": product_family,
                "recipe_id": recipe_id,
                "lot_id": lot_id,
                "failure_mode": failure_mode,
                "cycle_time_sec": round(max(cycle, 0.5), 4),
                "throughput_count": throughput,
                "target_throughput": target,
                "station_yield": round(station_yield, 5),
                "first_pass_yield": round(first_pass_yield, 5),
                "reject_count": rejects,
                "rework_count": rework,
                "defect_rate": round(defect_rate, 5),
                "micro_stop_count": micro_stops,
                "downtime_minutes": round(downtime, 4),
                "wip_count": wip,
                "queue_length": queue,
                "queue_time_minutes": round(queue * rng.uniform(0.2, 1.8), 3),
                "inspection_score_proxy": round(clamp(first_pass_yield - defect_rate * 0.4, 0.4, 0.999), 5),
                "process_stability_index": round(process_stability, 5),
                "operator_group": shift,
                "failure_label": future_failure,
                "rul_target": round(min(rul_target, 5000), 3),
                "future_failure_window": future_failure,
            }

            # Controlled data quality events separate from actual failures.
            dq_probability = 0.004 * cfg["dq"] * (1.35 if shift == "NIGHT" else 1.0)
            if rng.random() < dq_probability:
                issue = rng.choice(DQ_ISSUES)
                dq_event = {
                    "event_id": f"DQ_{state.machine_id}_{step:06d}_{issue}",
                    "site_id": state.site_id,
                    "area_id": state.area_id,
                    "line_id": state.line_id,
                    "machine_id": state.machine_id,
                    "station_id": state.station_id,
                    "timestamp": ts.isoformat(),
                    "issue_type": issue,
                    "severity": "high" if issue in {"IMPOSSIBLE_VALUE", "STUCK_SENSOR", "SENSOR_DROPOUT"} else "medium",
                    "affected_table": "sensor_readings" if "SENSOR" in issue or issue in {"MISSING_VALUE", "CLOCK_SKEW"} else "production_events",
                    "affected_column": rng.choice(["vibration_rms", "process_temperature", "cycle_time_sec", "throughput_count", "timestamp"]),
                    "details_json": json.dumps({"note": "synthetic data quality issue", "profile": profile}),
                }
                dq_rows.append(dq_event)
                if issue == "MISSING_VALUE":
                    sensor["vibration_rms"] = None
                elif issue == "IMPOSSIBLE_VALUE":
                    sensor["pressure"] = -5
                elif issue == "NEGATIVE_CYCLE_TIME":
                    prod["cycle_time_sec"] = -1.0
                elif issue == "ZERO_THROUGHPUT_WHILE_RUNNING":
                    prod["throughput_count"] = 0
                elif issue == "CLOCK_SKEW":
                    sensor["timestamp"] = (ts + timedelta(minutes=rng.randint(10, 45))).isoformat()
                elif issue == "OUT_OF_ORDER_EVENT":
                    prod["timestamp"] = (ts - timedelta(minutes=rng.randint(10, 30))).isoformat()

            if state.quality_excursion_remaining > 0 and rng.random() < 0.18:
                quality_rows.append({
                    "event_id": f"QUAL_{state.machine_id}_{step:06d}",
                    "site_id": state.site_id,
                    "area_id": state.area_id,
                    "line_id": state.line_id,
                    "machine_id": state.machine_id,
                    "station_id": state.station_id,
                    "timestamp": ts.isoformat(),
                    "lot_id": lot_id,
                    "product_family": product_family,
                    "quality_event_type": rng.choice(["FPY_DROP", "DEFECT_BURST", "REWORK_SPIKE", "INSPECTION_EXCURSION"]),
                    "severity": "high" if defect_rate > 0.10 else "medium",
                    "defect_rate": prod["defect_rate"],
                    "first_pass_yield": prod["first_pass_yield"],
                    "affected_units": max(1, rejects + rework),
                    "duration_minutes": rng.randint(args.interval_minutes, args.interval_minutes * 8),
                })

            sensor_rows.append(sensor)
            production_rows.append(prod)

    # Guarantee that the generated dataset contains at least one maintenance and
    # quality event so dashboard/report pages are populated for portfolio demos.
    if machines and not maintenance_rows:
        state = machines[0]
        forced_ts = start + timedelta(minutes=max(1, steps // 2) * args.interval_minutes)
        maintenance_rows.append({
            "event_id": f"MAINT_FORCED_{state.machine_id}_{int(forced_ts.timestamp())}",
            "site_id": state.site_id,
            "area_id": state.area_id,
            "line_id": state.line_id,
            "machine_id": state.machine_id,
            "station_id": state.station_id,
            "timestamp": forced_ts.isoformat(),
            "maintenance_type": "DEMO_TOOL_CHANGE",
            "reset_ratio": 0.45,
            "degradation_before": 0.72,
            "degradation_after": 0.32,
            "duration_minutes": 45.0,
        })
    if production_rows and not quality_rows:
        row = max(production_rows, key=lambda r: r.get("defect_rate", 0))
        quality_rows.append({
            "event_id": f"QUAL_FORCED_{row['machine_id']}_{row['timestamp'].replace(':', '').replace('-', '')}",
            "site_id": row["site_id"],
            "area_id": row["area_id"],
            "line_id": row["line_id"],
            "machine_id": row["machine_id"],
            "station_id": row["station_id"],
            "timestamp": row["timestamp"],
            "lot_id": row["lot_id"],
            "product_family": row["product_family"],
            "quality_event_type": "DEMO_FPY_DROP",
            "severity": "medium",
            "defect_rate": row["defect_rate"],
            "first_pass_yield": row["first_pass_yield"],
            "affected_units": max(1, row["reject_count"] + row["rework_count"]),
            "duration_minutes": args.interval_minutes * 3,
        })

    write_outputs(args, sensor_rows, production_rows, maintenance_rows, quality_rows, dq_rows)
    return {
        "sensor_rows": len(sensor_rows),
        "production_rows": len(production_rows),
        "maintenance_events": len(maintenance_rows),
        "quality_events": len(quality_rows),
        "data_quality_events": len(dq_rows),
        "failure_mode_distribution": dict(Counter(r["failure_mode"] for r in production_rows)),
        "shift_distribution": dict(Counter(r["shift"] for r in production_rows)),
        "profile": profile,
    }


def write_outputs(args: argparse.Namespace, sensor_rows: list[dict[str, Any]], production_rows: list[dict[str, Any]], maintenance_rows: list[dict[str, Any]], quality_rows: list[dict[str, Any]], dq_rows: list[dict[str, Any]]) -> None:
    output_db = Path(args.output_db)
    output_db.parent.mkdir(parents=True, exist_ok=True)
    repository.initialize_database(output_db)
    if args.reset:
        repository.reset_demo_tables(output_db)
    repository.insert_many("synthetic_machine_sensor_readings", sensor_rows, output_db)
    repository.insert_many("synthetic_production_events", production_rows, output_db)
    repository.insert_many("synthetic_maintenance_events", maintenance_rows, output_db)
    repository.insert_many("synthetic_quality_events", quality_rows, output_db)
    repository.insert_many("synthetic_data_quality_events", dq_rows, output_db)

    # Map to existing core pipeline tables.
    core_sensor = [
        {k: row.get(k) for k in ["event_id", "machine_id", "line_id", "station_id", "timestamp", "air_temperature", "process_temperature", "vibration_rms", "vibration_peak", "pressure", "torque", "rotational_speed", "motor_current", "power_consumption", "tool_wear", "production_load", "ambient_humidity"]} | {"operating_hours": row.get("hours_since_maintenance", 0) + row.get("machine_age_days", 0) * 24, "created_at": row.get("timestamp")}
        for row in sensor_rows
    ]
    core_prod = [
        {
            "event_id": row.get("event_id"),
            "line_id": row.get("line_id"),
            "station_id": row.get("station_id"),
            "batch_id": row.get("lot_id"),
            "shift": row.get("shift"),
            "timestamp": row.get("timestamp"),
            "cycle_time_sec": row.get("cycle_time_sec"),
            "throughput_count": row.get("throughput_count"),
            "target_throughput": row.get("target_throughput"),
            "station_yield": row.get("station_yield"),
            "reject_count": row.get("reject_count"),
            "rework_count": row.get("rework_count"),
            "defect_rate": row.get("defect_rate"),
            "micro_stop_count": row.get("micro_stop_count"),
            "downtime_minutes": row.get("downtime_minutes"),
            "wip_count": row.get("wip_count"),
            "queue_length": row.get("queue_length"),
            "inspection_score_proxy": row.get("inspection_score_proxy"),
            "process_stability_index": row.get("process_stability_index"),
            "operator_group": row.get("operator_group"),
            "created_at": row.get("timestamp"),
        }
        for row in production_rows
    ]
    repository.insert_many("sensor_readings", core_sensor, output_db)
    repository.insert_many("production_events", core_prod, output_db)
    for m in maintenance_rows:
        repository.insert_many("maintenance_events", [{"machine_id": m["machine_id"], "station_id": m["station_id"], "event_type": m["maintenance_type"], "event_timestamp": m["timestamp"], "details_json": json.dumps(m)}], output_db)
    for dq in dq_rows:
        repository.insert_data_quality_issues([{
            "issue_type": dq["issue_type"].lower(),
            "severity": dq["severity"],
            "entity_type": dq["affected_table"],
            "machine_id": dq["machine_id"],
            "line_id": dq["line_id"],
            "station_id": dq["station_id"],
            "timestamp": dq["timestamp"],
            "details_json": dq["details_json"],
        }], output_db)

    if args.output_csv_dir:
        out_dir = Path(args.output_csv_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, rows in [
            ("synthetic_machine_sensor_readings", sensor_rows),
            ("synthetic_production_events", production_rows),
            ("synthetic_maintenance_events", maintenance_rows),
            ("synthetic_quality_events", quality_rows),
            ("synthetic_data_quality_events", dq_rows),
        ]:
            path = out_dir / f"{name}.csv"
            if not rows:
                path.write_text("", encoding="utf-8")
                continue
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic smart manufacturing factory data.")
    parser.add_argument("--start-date", default="2026-05-01T06:00:00", help="ISO timestamp, e.g. 2026-05-01T06:00:00")
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--interval-minutes", type=int, default=5)
    parser.add_argument("--machines-per-line", type=int, default=8)
    parser.add_argument("--lines", type=int, default=4)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="normal_operation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-db", default="data/smart_factory.db")
    parser.add_argument("--output-csv-dir", default=None)
    parser.add_argument("--reset", action="store_true", help="Clear existing demo/core rows before inserting generated data.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = generate(args)
    print("Synthetic factory data generation summary")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
