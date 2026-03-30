# MQTT Adapter Documentation

## Overview
**File:** `Backend/src/base/infrastructure/mqtt_driver.py`

The `MqttDriver` class serves as the **Infrastructure Layer** gateway for all MQTT communication. It adheres to Clean Architecture principles by isolating low-level protocol details (using `aiomqtt`) from the business logic.

### Key Responsibilities
1.  **Connection Management**: Handles connecting/disconnecting from the MQTT broker.
2.  **Dispatcher**: Listens to subscribed topics and routes messages to registered callbacks.
3.  **Pattern Matching**: Supports MQTT wildcards (`+`, `#`) for routing.
4.  **Command Acknowledgment**: Implements a request-response mechanism over the asynchronous MQTT protocol using futures.

---

## Class: `MqttDriver`

### Constructor `__init__`
```python
def __init__(self, broker_url: str, broker_port: int, client_id: str = "backend"):
```
- **Purpose**: Initializes the adapter with broker connection details.
- **State Managed**:
    - `_callbacks`: Stores lists of functions triggered when a topic matches.
    - `_pending_responses`: A dictionary mapping `command_id` -> `asyncio.Future` used for tracking ACKs.

---

## Methods

### `on_message`
```python
def on_message(self, topic: str) -> Callable:
```
- **Type**: Decorator.
- **Purpose**: Registers a function as a handler for a specific MQTT topic.
- **Usage**:
  ```python
  @adapter.on_message("telemetry/temperature")
  async def handle_temp(topic, payload):
      pass
  ```
- **Note**: Supports multiple handlers per topic.

### `connect`
```python
async def connect(self):
```
- **Purpose**: Establishes the TCP connection to the MQTT broker using `aiomqtt`.
- **Behavior**: Non-blocking async connection. Logs success or failure.

### `disconnect`
```python
async def disconnect(self):
```
- **Purpose**: Gracefully closes the MQTT connection.

### `publish`
```python
async def publish(self, topic: str, payload: Union[Dict, str, bytes], qos: int = 0) -> bool:
```
- **Purpose**: Sends a message to a topic.
- **Features**:
    - Automatically serializes `dict` payloads to JSON strings.
    - Supports Quality of Service (QoS) levels 0, 1, or 2.
    - Returns `True` if successful, `False` on error.

### `publish_with_device_ack` (Critical Feature)
```python
async def publish_with_device_ack(self, topic: str, payload: Dict[str, Any], timeout: float = 5.0) -> bool:
```
- **Purpose**: Sends a command and **waits** for the device to reply that it received it.
- **Flow**:
    1. Generates a UUID `command_id` if missing.
    2. Creates an `asyncio.Future` and stores it in `_pending_responses`.
    3. Publishes the payload.
    4. Pauses execution using `asyncio.wait_for`.
    5. Returns `True` if `resolve_ack` is called before timeout, otherwise `False`.

### `resolve_ack`
```python
def resolve_ack(self, command_id: str) -> bool:
```
- **Purpose**: Called by an incoming message handler when an ACK is received.
- **Logic**: Looks up the `command_id` in `_pending_responses`. If found, it completes the future, causing the waiting `publish_with_device_ack` to resume instantly.

### `_topic_matches`
```python
def _topic_matches(self, pattern: str, topic: str) -> bool:
```
- **Purpose**: Internal utility to check if an incoming topic matches a subscription pattern.
- **Logic**:
    - `+`: Matches exactly one level (e.g., `sensors/+/temp` matches `sensors/1/temp`).
    - `#`: Matches all remaining levels (must be at the end, e.g., `sensors/#`).

### `run`
```python
async def run(self):
```
- **Purpose**: The main loop of the adapter.
- **Logic**:
    1. Connects if not already connected.
    2. Subscribes to all topics found in `_callbacks`.
    3. Enters an infinite async loop yielding messages.
    4. For every message, iterates `_callbacks` and uses `_topic_matches` to find handlers.
    5. Executes handlers as background tasks (`asyncio.create_task`) so one slow handler doesn't block the stream.

