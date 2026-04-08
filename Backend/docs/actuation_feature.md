# Actuation Feature

## Purpose

The actuation feature provides the command-and-control path for greenhouse devices. It lets the backend publish commands to a device through MQTT, wait for an acknowledgment, and surface that result through a FastAPI endpoint.

## Files in the slice

### `src/features/actuation/models.py`
Defines the domain model for actuation:

- `ActuationAction`: supported device actions.
- `ActuationCommand`: immutable domain command that inherits from `base.domain.command.Command`.

`ActuationCommand` validates that:

- `device_id` is not empty
- `action` is a valid `ActuationAction`
- `parameters` is either `None` or a dictionary

### `src/features/actuation/service.py`
Contains `ActuationService`, which is responsible for:

- transforming the domain command into the MQTT payload
- publishing the payload through `MqttDriver`
- waiting for the device acknowledgment
- resolving ACKs by command ID

### `src/features/actuation/router.py`
Defines the HTTP transport adapter for the feature.

Endpoint:

- `POST /api/v1/actuation/{device_id}/command`

The endpoint:

- accepts `action` and optional `parameters`
- builds an `ActuationCommand`
- calls the actuation service
- returns `200 OK` when the device ACK is received
- returns `504 Gateway Timeout` when the ACK is not received in time

### `src/features/actuation/listeners.py`
Contains the MQTT listener logic that closes the feedback loop.

- `handle_ack_message(...)` extracts `command_id` and resolves the pending future.
- `register_actuation_ack_listener(...)` subscribes to `commands/greenhouse/+/ack` and routes ACK messages to the resolver.

### `src/features/actuation/__init__.py`
Exposes the public API of the feature slice:

- `ActuationAction`
- `ActuationCommand`
- `ActuationService`
- `handle_ack_message`
- `register_actuation_ack_listener`
- `router`

## Runtime flow

1. A client sends a request to the HTTP endpoint.
2. The router converts the request into a domain `ActuationCommand`.
3. `ActuationService` publishes the command to:
   - `commands/greenhouse/{device_id}`
4. `MqttDriver` stores a pending future keyed by `command_id`.
5. The device processes the command and sends an ACK on:
   - `commands/greenhouse/{device_id}/ack`
6. The listener decodes the JSON ACK payload.
7. The listener extracts `command_id` and resolves the matching future.
8. The HTTP route returns success if the ACK arrives before timeout.

## Example ACK payload

```json
{
  "command_id": "8c3b77f4-4adf-4a77-8c4a-9c1b21b0f4f2"
}
```

## Notes

- The feature intentionally reuses the shared domain `Command` base class so actuation commands follow the same command semantics as the rest of the system.
- The MQTT driver keeps the actual request-reply waiting logic; the feature service stays thin and focused on the actuation use case.

