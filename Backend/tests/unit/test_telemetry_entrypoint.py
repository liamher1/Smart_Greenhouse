import json
import unittest
from datetime import datetime, timezone

from Backend.src.features.telemetry.entrypoints import TelemetryEntrypoint
from Backend.src.features.telemetry.events import TelemetryRecorded


class FakeMessageBus:
    def __init__(self):
        self.messages = []

    async def handle(self, message):
        self.messages.append(message)


class TestTelemetryEntrypoint(unittest.IsolatedAsyncioTestCase):
    async def test_dispatches_valid_telemetry_event(self):
        bus = FakeMessageBus()
        entrypoint = TelemetryEntrypoint(bus)

        payload = {
            "header": {
                "type": "telemetry",
                "device_id": "esp32-1",
                "timestamp": "2026-04-04T10:00:00+00:00",
            },
            "payload": {
                "temperature": 26.3,
                "humidity": 45.0,
            },
        }

        await entrypoint.on_telemetry_message("greenhouse/telemetry/esp32-1", json.dumps(payload).encode("utf-8"))

        self.assertEqual(len(bus.messages), 1)
        event = bus.messages[0]
        self.assertIsInstance(event, TelemetryRecorded)
        self.assertEqual(event.device_id, "esp32-1")
        self.assertEqual(event.timestamp, datetime(2026, 4, 4, 10, 0, tzinfo=timezone.utc))

    async def test_ignores_non_telemetry_message_type(self):
        bus = FakeMessageBus()
        entrypoint = TelemetryEntrypoint(bus)

        payload = {
            "header": {
                "type": "ack",
                "device_id": "esp32-1",
                "timestamp": "2026-04-04T10:00:00+00:00",
            },
            "payload": {
                "temperature": 26.3,
                "humidity": 45.0,
            },
        }

        await entrypoint.on_telemetry_message("greenhouse/telemetry/esp32-1", json.dumps(payload).encode("utf-8"))

        self.assertEqual(bus.messages, [])

    async def test_rejects_invalid_payload_values(self):
        bus = FakeMessageBus()
        entrypoint = TelemetryEntrypoint(bus)

        payload = {
            "header": {
                "type": "telemetry",
                "device_id": "esp32-1",
                "timestamp": "2026-04-04T10:00:00+00:00",
            },
            "payload": {
                "temperature": 26.3,
                "humidity": 145.0,
            },
        }

        await entrypoint.on_telemetry_message("greenhouse/telemetry/esp32-1", json.dumps(payload).encode("utf-8"))

        self.assertEqual(bus.messages, [])


if __name__ == "__main__":
    unittest.main()

