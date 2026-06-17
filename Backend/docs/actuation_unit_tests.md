# Actuation Unit Tests

## Overview

Unit tests verify each component of the actuation slice in isolation without any external infrastructure.

- No real MQTT broker.
- No database.
- Uses `FakeMqttDriver` and `FakeActuationService` in place of real infrastructure.

## Test File

- `tests/unit/features/actuation/test_actuation_unit.py`

## Covered Tests

### `ActuationCommand` validation (9 tests)

- `test_valid_command_creates_successfully` — happy-path command creation.
- `test_empty_device_id_raises` — empty string is rejected.
- `test_whitespace_only_device_id_raises` — blank string is rejected.
- `test_device_id_is_stripped_of_whitespace` — leading/trailing spaces are removed.
- `test_parameters_must_be_dict_when_provided` — non-dict parameters raises `ValueError`.
- `test_none_parameters_is_valid` — `None` is explicitly allowed.
- `test_dict_parameters_are_valid` — arbitrary dict is accepted.
- `test_each_command_has_unique_id` — two commands with the same fields get different `command_id` values.
- `test_all_action_variants_are_accepted` — all four `ActuationAction` enum values are valid.

### `ActuationService` (8 tests)

- `test_service_publishes_to_correct_topic` — topic format is `commands/greenhouse/{device_id}`.
- `test_service_includes_required_fields_in_payload` — `command_id`, `device_id`, `action`, `timestamp` are always present.
- `test_service_includes_parameters_when_present` — parameters dict forwarded into payload when set.
- `test_service_omits_parameters_key_when_none` — `parameters` key is absent from payload when not provided.
- `test_service_returns_true_when_driver_acks` — propagates driver `True`.
- `test_service_returns_false_when_driver_times_out` — propagates driver `False`.
- `test_service_resolve_ack_delegates_to_driver` — `resolve_ack` passes command_id to driver.
- `test_service_resolve_ack_returns_false_when_not_pending` — returns driver `False` unchanged.

### `handle_ack_message` listener (3 tests)

- `test_ack_listener_returns_false_when_command_id_missing` — missing `command_id` in payload returns `False` without calling service.
- `test_ack_listener_calls_resolve_with_command_id` — valid `command_id` is forwarded to `service.resolve_ack`.
- `test_ack_listener_returns_false_when_no_pending_command` — returns `False` when service reports no pending command.

### `RuleTriggeredHandler` (4 tests)

- `test_handler_publishes_command_for_valid_action` — event with a known action builds and publishes an `ActuationCommand`.
- `test_handler_drops_event_with_unknown_action` — invalid action string is logged and dropped; service is never called.
- `test_handler_includes_pulse_duration_in_parameters_when_nonzero` — `pulse_duration_ms > 0` populates `parameters`.
- `test_handler_omits_parameters_when_pulse_duration_is_zero` — `pulse_duration_ms == 0` leaves `parameters` as `None`.

## Why It Matters

These tests lock in the payload contract between the backend and ESP32 firmware (topic format, required fields, enum values) and protect against regressions in the handler's action-guard and parameter-mapping logic.

## Run

Run from `Backend/`.

```powershell
python -m pytest tests/unit/features/actuation/ -q
```

## Troubleshooting

- If imports fail, confirm `pytest.ini` has `pythonpath = src`.
- `FakeMqttDriver` and `FakeActuationService` are defined locally in the test file — no shared conftest needed.
