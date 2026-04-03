# Telemetry E2E Tests

This folder documents and hosts end-to-end style tests for the telemetry slice.

## Scope

Current test: `test_telemetry_ingestion_flow.py`

It validates the in-process telemetry path:

1. Raw MQTT-like payload bytes arrive at `TelemetryEntrypoint`.
2. Envelope + payload are validated and transformed into `TelemetryRecorded`.
3. `MessageBus` dispatches the event to `TelemetryEventHandler`.
4. Handler maps event data to `TelemetryReading` and calls repository persistence.

## Why this is "E2E-style" and not full external E2E

The test uses lightweight fakes:

- `FakeSession` and `FakeTransaction` replace real DB session/transaction behavior.
- `CapturingRepository` stores persisted objects in memory for assertions.

This keeps the test fast and deterministic while still checking full slice orchestration.

## What is asserted

For a valid telemetry message, the test asserts:

- Exactly one reading is persisted.
- `device_id`, `temperature`, and `humidity` are propagated correctly.
- The event timestamp from the envelope header is preserved in persistence model.

## Run only e2e tests

```powershell
python -m unittest discover -s Backend/tests/e2e -p "test_*.py" -v
```

## Extend with additional scenarios

Recommended next cases:

- Invalid telemetry value should not persist.
- Non-`telemetry` message type should be ignored.
- Repository failure should trigger rollback path and bubble exception as expected.

