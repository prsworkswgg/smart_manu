# SensorCollector - C# Data Acquisition Service

`SensorCollector` is a .NET 8 console application for the Smart Manufacturing AI Operations Platform. It simulates machine sensor readings and production-line events, then posts them to a FastAPI backend.

This service uses simulated industrial data only. It does not use real Seagate data, proprietary factory data, or validated production data.

## Responsibilities

- Read runtime configuration from `appsettings.json`
- Simulate machine sensor readings
- Simulate production-line process events
- Send records to FastAPI:
  - `POST /ingest/sensor-reading`
  - `POST /ingest/production-event`
- Buffer failed records into local JSONL files when the API is down
- Retry buffered records later
- Log activity to the console
- Support `realtime` and `batch` modes
- Support graceful shutdown with Ctrl+C

## .NET Version

Target framework: `.NET 8`

```bash
dotnet --version
```

## Project Structure

```text
acquisition-csharp/SensorCollector/
├── SensorCollector.csproj
├── Program.cs
├── Models/
│   ├── SensorReading.cs
│   ├── ProductionEvent.cs
│   ├── MachineConfig.cs
│   ├── CollectorSettings.cs
│   └── CollectorStatus.cs
├── Services/
│   ├── MachineSensorSimulator.cs
│   ├── ProductionLineSimulator.cs
│   ├── ApiPublisher.cs
│   ├── LocalBufferWriter.cs
│   ├── RetryQueue.cs
│   └── HealthCheckClient.cs
├── appsettings.json
└── README.md
```

## How to Create the Project

From the repository root:

```bash
mkdir -p acquisition-csharp
cd acquisition-csharp

dotnet new console -n SensorCollector --framework net8.0 --force
cd SensorCollector
```

Replace the generated files with the files in this phase.

## How to Build

```bash
cd acquisition-csharp/SensorCollector
dotnet restore
dotnet build
```

## How to Run

Start FastAPI first, then run:

```bash
cd acquisition-csharp/SensorCollector
dotnet run
```

Run with a custom config:

```bash
dotnet run -- --config appsettings.json
```

## Realtime Mode

Set this in `appsettings.json`:

```json
"CollectionSettings": {
  "Mode": "realtime",
  "SampleIntervalMs": 1000
}
```

The collector generates one sensor reading and one production event per configured station every interval.

## Batch Mode

Set this in `appsettings.json`:

```json
"CollectionSettings": {
  "Mode": "batch",
  "BatchSize": 25,
  "BatchDelaySeconds": 10
}
```

The collector generates `BatchSize` cycles quickly, posts them, then waits before the next batch.

## Local Buffer

If FastAPI is unavailable, records are saved as JSONL:

```text
local-buffer/sensor_readings_buffer.jsonl
local-buffer/production_events_buffer.jsonl
```

The retry loop periodically reads these files and attempts to repost the records.

## Expected Console Output

Healthy API:

```text
============================================================
 Smart Manufacturing AI Operations Platform
 C# Data Acquisition Service - Simulated Data Only
============================================================
[CONFIG] mode=realtime, api=http://127.0.0.1:8000, machines=7
[DISCLAIMER] Simulated data only. No real Seagate or proprietary factory data.
[START] Station simulators initialized: 7
[MODE] Realtime mode. sample_interval_ms=1000
[RETRY] Retry loop enabled. interval_seconds=15
[SEND] sensor ok MTR_PRESS_01/ST_PRESS_01 wear=18.01 vib=1.324
[SEND] production ok LINE_A/ST_PRESS_01 cycle=5.12s yield=0.9812
[STATUS] uptime=00:00:03, sensor_generated=7, production_generated=7, sensor_sent=7, production_sent=7, sensor_buffered=0, production_buffered=0, retry_ok=0, retry_failed=0, api_failures=0
```

API down:

```text
[BUFFER] API unavailable. buffered sensor+production for MTR_PRESS_01/ST_PRESS_01
[STATUS] uptime=00:00:10, sensor_generated=14, production_generated=14, sensor_sent=0, production_sent=0, sensor_buffered=14, production_buffered=14, retry_ok=0, retry_failed=0, api_failures=14
```

## How to Check FastAPI Received Data

Use the FastAPI health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Check acquisition status after Phase 2 backend exists:

```bash
curl http://127.0.0.1:8000/data-acquisition/status
```

Check SQLite directly:

```bash
sqlite3 database/smart_manufacturing.db "select count(*) from sensor_readings;"
sqlite3 database/smart_manufacturing.db "select count(*) from production_events;"
```

## Simulation Logic

The simulator encodes simple manufacturing relationships:

- `tool_wear` increases with `operating_hours`
- high `tool_wear` increases `torque`
- high `torque` increases `motor_current`
- high `tool_wear` and high `torque` increase `vibration_rms`
- high `vibration_rms` increases `cycle_time_sec`
- high `cycle_time_sec` increases `micro_stop_count`
- high defect risk increases `defect_rate`
- high `defect_rate` lowers `station_yield`
- process-temperature drift lowers `process_stability_index`
- simple maintenance reset partially reduces tool wear and temperature drift

## Validation Checklist

- [ ] `dotnet restore` succeeds
- [ ] `dotnet build` succeeds
- [ ] `dotnet run` starts the collector
- [ ] Collector reads `appsettings.json`
- [ ] Collector logs machine and station IDs
- [ ] Collector sends sensor readings to `/ingest/sensor-reading`
- [ ] Collector sends production events to `/ingest/production-event`
- [ ] If API is down, JSONL buffer files are created
- [ ] When API returns, retry loop sends buffered records
- [ ] `Ctrl+C` shuts down gracefully

## Common Errors

### `dotnet: command not found`

Install .NET 8 SDK and confirm:

```bash
dotnet --version
```

### `appsettings.json was not found`

Run from the project directory:

```bash
cd acquisition-csharp/SensorCollector
dotnet run
```

Or pass config explicitly:

```bash
dotnet run -- --config /path/to/appsettings.json
```

### API rejects payload with 422

The FastAPI Pydantic schema probably does not match the C# JSON contract. Confirm that the backend expects these field names:

```text
machine_id, line_id, station_id, timestamp, air_temperature, process_temperature,
vibration_rms, vibration_peak, pressure, torque, rotational_speed, motor_current,
power_consumption, tool_wear, operating_hours, production_load, ambient_humidity
```

and:

```text
line_id, station_id, batch_id, shift, timestamp, cycle_time_sec, throughput_count,
target_throughput, station_yield, reject_count, rework_count, defect_rate,
micro_stop_count, downtime_minutes, wip_count, queue_length,
inspection_score_proxy, process_stability_index, operator_group
```

### Buffer keeps growing

FastAPI is still down or the endpoint paths are wrong. Check:

```bash
curl http://127.0.0.1:8000/health
```

Then check `ApiSettings` in `appsettings.json`.

### Program exits immediately

If `RunMinutes` is greater than zero, the collector stops after that many minutes. Use `0` for infinite run.
