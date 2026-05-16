# Synthetic Data Dictionary

## synthetic_machine_sensor_readings

Stores high-detail synthetic sensor readings. Includes site, area, line, machine, station, shift, load state, product family, recipe, lot, failure mode, environmental conditions, hidden degradation state, and sensor values.

Important: `hidden_degradation_state` is a simulation variable and must not be used as a training feature.

## synthetic_production_events

Stores production-line outcomes linked to sensor degradation. Includes cycle time, throughput, target throughput, first-pass yield, defect rate, micro-stops, downtime, WIP, queue length, process stability, synthetic failure label, and RUL target.

## synthetic_maintenance_events

Stores planned or triggered synthetic maintenance events. Maintenance partially resets degradation and creates post-maintenance recovery behavior.

## synthetic_quality_events

Stores burst-style quality excursions such as FPY drop, defect burst, rework spike, or inspection excursion.

## synthetic_data_quality_events

Stores data quality issues that are separate from actual machine failures. Examples include missing value, duplicate event, timestamp gap, out-of-order event, stuck sensor, dropout, impossible value, delayed message, clock skew, negative cycle time, and zero throughput while running.

## Core mapped tables

The generator also maps compatible fields into the existing `sensor_readings` and `production_events` tables so preprocessing, ML, and dashboard flows continue to work.
