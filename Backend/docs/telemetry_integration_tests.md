# Telemetry Integration Tests

## Overview

Integration tests validate telemetry persistence against a real PostgreSQL instance.

- Real `TelemetryEventHandler`.
- Real `TelemetryRepository`.
- Ephemeral PostgreSQL from `testcontainers`.

## Test File

- `tests/integration/features/telemetry/test_telemetry_event_handler_integration.py`

## Covered Test

### `test_handler_persists_telemetry_to_real_postgres`

Verifies that a `TelemetryRecorded` event passed directly to the handler is persisted in PostgreSQL with expected fields:

- `temperature`
- `humidity`
- `device_id`
- `timestamp`
- generated row `id`

## Environment Requirements

- Docker daemon running.
- Python package `testcontainers` installed.
- Async DB driver used by SQLAlchemy URL (`asyncpg`).

## Run

Run from `Backend/`.

```powershell
python -m pytest tests/integration/features/telemetry/test_telemetry_event_handler_integration.py -q
```

Or by marker:

```powershell
python -m pytest -m integration -q
```

## Troubleshooting

- If container startup fails, check Docker Desktop status.
- If DB connection fails, verify container networking and no local firewall block.
- If schema errors appear, confirm models are included in `SQLModel.metadata`.

