# Data Simulation Design

## Goal

The simulation creates manufacturing-like relationships instead of unrelated random columns.

## Sensor data

Sensor readings include:

- air temperature
- process temperature
- vibration RMS and peak
- pressure
- torque
- rotational speed
- motor current
- power consumption
- tool wear
- operating hours
- production load
- ambient humidity

## Production data

Production events include:

- cycle time
- throughput
- target throughput
- station yield
- reject count
- rework count
- defect rate
- micro-stop count
- downtime
- WIP
- queue length
- inspection score proxy
- process stability index

## Causal relationships

The simulator encodes these relationships:

```text
operating_hours increases
-> tool_wear increases

tool_wear high
-> torque high

torque high
-> motor_current high

tool_wear and torque high
-> vibration high

vibration high
-> cycle_time increases

cycle_time high
-> micro_stop_count increases

defect_rate high
-> station_yield decreases

process_temperature drift
-> process_stability_index decreases
```

## Maintenance reset

A simple maintenance reset partially reduces tool wear and temperature drift and temporarily damps vibration.

## Data quality issues

The platform can detect or simulate:

- missing values
- duplicate timestamps
- timestamp gaps
- sensor dropout
- stuck sensor
- delayed readings
- impossible values

## Limitations

The simulation is useful for demonstrating workflow and software design, but it is not a substitute for real factory data, maintenance records, or process-owner validation.
