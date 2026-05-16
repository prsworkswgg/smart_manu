# Synthetic Simulation Design

## Positioning

Synthetic HDD / Precision Electronics Smart Manufacturing Dataset inspired by public high-level information about manufacturing operations in Thailand. No real Seagate data. No proprietary data. No real factory deployment.

## Sites and areas

Sites:

- TH_PRECISION_SITE_A
- TH_COMPONENT_SITE_B

Synthetic process areas:

- AREA_01_SLIDER_PROCESSING
- AREA_02_HEAD_ASSEMBLY
- AREA_03_HGA_ASSEMBLY
- AREA_04_DRIVE_ASSEMBLY
- AREA_05_FINAL_TEST
- AREA_06_REWORK_INSPECTION
- AREA_07_PACKAGING

## Profiles

- normal_operation
- early_degradation
- unstable_process
- quality_excursion
- post_maintenance_recovery
- high_load_stress
- data_quality_incident

## Key causal assumptions

- Higher tool wear increases vibration and process temperature.
- Higher vibration, temperature, and tool wear increase defect risk.
- Degradation increases cycle time, micro-stops, queue pressure, and downtime.
- Quality excursions are bursts, not isolated random points.
- Maintenance partially resets hidden degradation and produces a recovery period.
- Night shift slightly increases data quality risk and delay risk.

These are synthetic assumptions for workflow demonstration. They are not real process parameters.
