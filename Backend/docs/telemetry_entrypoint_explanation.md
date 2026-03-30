# Telemetry Entrypoint Documentation

## Overview
**File:** `Backend/src/features/telemetry/entrypoints.py`

This module serves as the **Interface Adapter** for the Telemetry feature. It acts as the bridge between the external MQTT infrastructure and the internal domain layer.

It is responsible for:
1.  Receiving raw MQTT messages.
2.  Validating them against strict schemas (`IncomingMqttDto`).
3.  transforming them into Domain Events (`TelemetryRecorded`).
4.  Dispatching these events to the internal Message Bus.

---

## Class: `TelemetryEntrypoint`

### Constructor `__init__`
```python
def __init__(self, message_bus: MessageBus):
```
- **Purpose**: Initializes the entrypoint with a reference to the `MessageBus`.
- **Dependency**: Requires a valid `MessageBus` instance to dispatch events into the system.

### `on_telemetry_message`
```python
async def on_telemetry_message(self, topic: str, payload: bytes):
```
- **Purpose**: The main callback function executed when an MQTT message arrives on the telemetry topic.
- **Arguments**:
    - `topic`: The specific topic the message resolved to (e.g., `greenhouse/telemetry/sensor-01`).
    - `payload`: The raw byte content of the message.
- **Process Flow**:
    1.  **Decoding**: Converts raw bytes to a UTF-8 string and parses it as JSON.
    2.  **Schema Validation**: 
        - Wraps the data in a `IncomingMqttDto` Pydantic model.
        - Ensures the message structure (Header + Payload) is valid.
    3.  **Type Check**: Verifies the `header.type` is explicitly "telemetry".
    4.  **Payload Extraction**: Extracts payload fields and injects `device_id` from the envelope header.
    5.  **Event Creation**: Instantiates a `TelemetryRecorded` domain model.
    6.  **Dispatch**: Sends the event to the `MessageBus` for handling by business logic handlers.

- **Error Handling**:
    - Catches `json.JSONDecodeError` for malformed JSON.
    - Catches `pydantic.ValidationError` for invalid schemas.
    - Logs errors without crashing the application.

---

## Functions

### `register_telemetry_entrypoint`
```python
def register_telemetry_entrypoint(mqtt_driver, message_bus: MessageBus):
```
- **Purpose**: Wiring function to connect this feature to the infrastructure.
- **Logic**:
    1.  Instantiates `TelemetryEntrypoint` with the provided `message_bus`.
    2.  Uses the `mqtt_driver.on_message` method to register `entrypoint.on_telemetry_message` to the topic pattern `greenhouse/telemetry/+`.
    -   The `+` wildcard allows capturing messages from any partial topic at that level (e.g., any device ID).

