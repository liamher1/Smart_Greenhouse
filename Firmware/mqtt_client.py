import json
from umqtt.simple import MQTTClient as _SimpleClient
from config import MQTT_BROKER, MQTT_PORT, DEVICE_ID

_client = None
_command_cb = None

# Topic this device listens on for actuation commands
COMMAND_TOPIC = f"commands/greenhouse/{DEVICE_ID}"


def _on_raw_message(topic, payload):
    if _command_cb is None:
        return
    try:
        data = json.loads(payload)
        _command_cb(topic.decode(), data)
    except Exception as e:
        print(f"mqtt_client: failed to dispatch message: {e}")


def connect(on_command):
    """Connect to the broker, subscribe to the command topic, and register the command callback."""
    global _client, _command_cb
    _command_cb = on_command
    _client = _SimpleClient(DEVICE_ID, MQTT_BROKER, port=MQTT_PORT)
    _client.set_callback(_on_raw_message)
    _client.connect()
    _client.subscribe(COMMAND_TOPIC)
    print(f"MQTT connected — subscribed to {COMMAND_TOPIC}")


def publish(topic, payload_dict):
    """Publish a dict as JSON to the given topic."""
    if _client is None:
        raise RuntimeError("mqtt_client.connect() must be called before publish()")
    _client.publish(topic, json.dumps(payload_dict))


def check_msg():
    """Non-blocking poll for incoming messages. Call once per main-loop iteration."""
    if _client:
        _client.check_msg()
