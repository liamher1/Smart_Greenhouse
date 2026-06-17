# Actuation End-to-End Tests

## Overview

E2E tests validate the complete actuation request-reply loop as a black-box system:

```
HTTP POST → ActuationService → MqttDriver → Mosquitto broker
    → device simulator (ACK) → ACK listener → resolve future → HTTP 200
```

A disposable Mosquitto container (testcontainers) is spun up automatically. A lightweight
in-test "device simulator" subscribes to the command topic and publishes the ACK, so no
real ESP32 hardware is required.

## Test File

- `tests/e2e/features/actuation/test_actuation_e2e.py`

## Covered Tests

### `test_actuation_command_reaches_device_and_returns_200`

Verifies the full happy-path round-trip:

1. Backend connects to broker, registers ACK listener.
2. Device simulator subscribes to `commands/greenhouse/{device_id}`.
3. HTTP POST fires; `ActuationService` publishes the command.
4. Device simulator receives the command and publishes an ACK.
5. ACK listener resolves the pending future.
6. HTTP response returns `200 accepted`.

### `test_actuation_command_with_parameters_reaches_device`

Same flow as above, additionally verifying that:

- `parameters` sent in the request body (`{"pulse_duration_ms": 400}`) appear verbatim in the MQTT payload received by the device.

### `test_actuation_returns_504_when_no_device_responds`

Verifies the timeout path:

- No device simulator is started.
- `publish_with_device_ack` waits 5 s with no ACK and returns `False`.
- HTTP response returns `504 Gateway Timeout` with a "Timed out" detail.

## Environment Requirements

- Docker daemon running.
- Python packages: `aiomqtt`, `testcontainers`, Docker SDK (`docker`).
- Network access for the ephemeral Mosquitto container.

Tests skip automatically with a clear reason when Docker is unavailable.

## Run

Run from `Backend/`.

```powershell
python -m pytest tests/e2e/features/actuation/ -q
```

Or by marker:

```powershell
python -m pytest -m e2e -q
```

## Troubleshooting

- **Skipped** — Docker daemon is not running or the optional packages are missing.
- **Timeout in happy-path test** — the device simulator may have failed to subscribe before the POST fired. The test awaits `device_ready` before posting; if that times out, check broker container startup logs.
- **504 in happy-path test** — verify that `register_actuation_ack_listener` is called before `mqtt_driver.run()` so the ACK subscription is registered.
- **Windows async issues** — the module sets `WindowsSelectorEventLoopPolicy` at import time, which is required for `aiomqtt` on Windows.
