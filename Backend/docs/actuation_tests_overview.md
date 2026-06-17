# Actuation Test Suites

This document is the index for actuation testing docs.

The actuation slice is tested with three levels:

1. Unit tests: validate model validation, service payload logic, listener, and handler in isolation with fakes.
2. Integration tests: validate the HTTP router against a real FastAPI app (no broker required).
3. End-to-end tests: validate the full MQTT request-reply loop with a real Mosquitto container.

## Test Docs

- `docs/actuation_unit_tests.md`
- `docs/actuation_integration_tests.md`
- `docs/actuation_e2e_tests.md`

## Quick Run Commands

Run from `Backend/`.

```powershell
python -m pytest tests/unit/features/actuation/ -q
python -m pytest tests/integration/features/actuation/ -q
python -m pytest tests/e2e/features/actuation/ -q
```

Run by marker:

```powershell
python -m pytest -m integration -q
python -m pytest -m e2e -q
```
