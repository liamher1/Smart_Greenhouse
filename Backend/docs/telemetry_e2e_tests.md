# Telemetry End-to-End Tests

## Overview

E2E tests validate the complete telemetry ingestion flow as a black-box system:

MQTT publish -> MQTT driver -> telemetry entrypoint -> message bus -> handler -> PostgreSQL

## Test File

- `tests/e2e/features/telemetry/test_telemetry_ingestion_e2e.py`

## Covered Test

### `test_mqtt_publish_is_ingested_and_saved_to_db`

Verifies that an externally published MQTT telemetry JSON payload is:

1. consumed by the backend listener,
2. transformed into `TelemetryRecorded`,
3. persisted in PostgreSQL,
4. queryable with exact expected values.

The test includes polling to handle asynchronous processing and ensure deterministic assertion timing.

## Environment Requirements

- Docker daemon running.
- Python packages: `aiomqtt`, `testcontainers`, Docker SDK.
- Network access for ephemeral Mosquitto and Postgres containers.

## Run

Run from `Backend/`.

```powershell
python -m pytest tests/e2e/features/telemetry/test_telemetry_ingestion_e2e.py -q
```

Or by marker:

```powershell
python -m pytest -m e2e -q
```

## Troubleshooting

- Skipped test usually means missing optional dependencies or Docker unavailable.
- If message is published but not persisted, verify both wiring steps at startup:
  - telemetry entrypoint registration,
  - message bus subscription for `TelemetryRecorded`.
- On Windows async issues, confirm event loop policy handling in the test module.

