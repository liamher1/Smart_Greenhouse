# Telemetry Test Suites

This document is the index for telemetry testing docs.

The telemetry slice is tested with three levels:

1. Unit tests: validate handler behavior in isolation with fakes.
2. Integration tests: validate handler and repository against real PostgreSQL.
3. End-to-end tests: validate MQTT publish -> entrypoint -> bus -> handler -> PostgreSQL.

## Test Docs

- `docs/telemetry_unit_tests.md`
- `docs/telemetry_integration_tests.md`
- `docs/telemetry_e2e_tests.md`

## Quick Run Commands

Run from `Backend/`.

```powershell
python -m pytest tests/unit/features/telemetry/test_telemetry_event_handler_unit.py -q
python -m pytest tests/integration/features/telemetry/test_telemetry_event_handler_integration.py -q
python -m pytest tests/e2e/features/telemetry/test_telemetry_ingestion_e2e.py -q
```

Run by marker:

```powershell
python -m pytest -m integration -q
python -m pytest -m e2e -q
```

