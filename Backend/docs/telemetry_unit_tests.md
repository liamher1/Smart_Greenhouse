# Telemetry Unit Tests

## Overview

Unit tests verify `TelemetryEventHandler` logic without external infrastructure.

- No real database.
- No MQTT.
- Uses `FakeSession`, `FakeTransaction`, and `FakeRepository`.

## Test File

- `tests/unit/features/telemetry/test_telemetry_event_handler_unit.py`

## Covered Tests

### `test_handler_opens_transaction_saves_and_closes_session`

Verifies the happy path:

- opens one session,
- opens one transaction,
- saves exactly one reading through repository,
- does not call rollback,
- closes the session.

### `test_handler_rolls_back_and_reraises_when_repository_fails`

Verifies error behavior:

- repository failure is propagated (re-raised),
- rollback is called once,
- session is still closed,
- transaction context exits cleanly.

## Why It Matters

These tests lock in per-message unit-of-work behavior and protect against regressions in transaction handling logic.

## Run

Run from `Backend/`.

```powershell
python -m pytest tests/unit/features/telemetry/test_telemetry_event_handler_unit.py -q
```

## Troubleshooting

- If imports fail, confirm `pytest.ini` has `pythonpath = src`.
- If test names change, update this doc to keep it aligned with code.

