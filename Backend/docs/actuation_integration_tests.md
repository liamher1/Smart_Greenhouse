# Actuation Integration Tests

## Overview

Integration tests verify the FastAPI HTTP router layer integrated with the application service.
A real FastAPI app is constructed with a `FakeActuationService` attached to `app.state`, and
requests are issued via `httpx.AsyncClient`. No MQTT broker or database is required.

## Test File

- `tests/integration/features/actuation/test_actuation_integration.py`

## Covered Tests

### Happy path (4 tests)

- `test_post_returns_200_and_accepted_when_device_acks` — response body contains `status`, `device_id`, `action`, `command_id`, and `timestamp`.
- `test_post_forwards_parameters_to_service` — parameters from the request body reach the `ActuationCommand` passed to the service.
- `test_post_accepts_all_valid_actions` — all four `ActuationAction` values return 200.
- `test_post_without_parameters_sends_none_to_service` — omitting `parameters` from the body sends `None` to the service.

### Error paths (5 tests)

- `test_post_returns_504_when_device_does_not_ack` — service returning `False` produces a `504 Gateway Timeout` with a "Timed out" detail.
- `test_post_returns_503_when_actuation_service_is_not_configured` — missing `app.state.actuation_service` returns `503`.
- `test_post_returns_422_for_invalid_action_value` — unknown action string produces `422 Unprocessable Entity`.
- `test_post_returns_422_when_action_is_missing` — empty body produces `422`.
- `test_device_id_comes_from_path_not_body` — the path segment, not the body, sets `command.device_id`.

## Environment Requirements

- No external services needed.
- `httpx` is included via `fastapi[all]` in `requirements.txt`.

## Run

Run from `Backend/`.

```powershell
python -m pytest tests/integration/features/actuation/ -q
```

Or by marker:

```powershell
python -m pytest -m integration -q
```

## Troubleshooting

- `503` seen unexpectedly — check that the fixture is attaching `service` to `app.state.actuation_service`.
- `422` on a valid action — verify the request body uses the string value of the enum (e.g., `"PUMP_ON"`, not the Python attribute name).
