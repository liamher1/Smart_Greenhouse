"""E2E-style test for telemetry ingestion flow.

This test runs the full in-process path:
raw MQTT payload bytes -> telemetry entrypoint -> message bus -> event handler -> repository.

It uses lightweight fakes for session and repository so the test validates orchestration
without requiring a live MQTT broker or PostgreSQL instance.
"""

import json
import unittest

from Backend.src.base.infrastructure.message_bus import MessageBus
from Backend.src.features.telemetry.entrypoints import TelemetryEntrypoint
from Backend.src.features.telemetry.events import TelemetryRecorded
from Backend.src.features.telemetry.handlers import TelemetryEventHandler


class FakeTransaction:
    """Minimal async transaction context used by ``FakeSession.begin()`` in tests."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        self._session.in_tx = True
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        self._session.in_tx = False
        return False


class FakeSession:
    """Small async session fake that tracks transaction state and close behavior."""

    def __init__(self):
        self.closed = False
        self.in_tx = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        self.closed = True

    def begin(self):
        return FakeTransaction(self)

    def in_transaction(self):
        return self.in_tx

    async def rollback(self):
        self.in_tx = False


class CapturingRepository:
    """Repository fake that captures persisted readings for assertions."""

    stored_readings = []

    def __init__(self, _session):
        pass

    async def add_telemetry_reading(self, telemetry_reading):
        CapturingRepository.stored_readings.append(telemetry_reading)


class TestTelemetryIngestionE2E(unittest.IsolatedAsyncioTestCase):
    """Verifies telemetry message ingestion through the full in-process slice."""

    async def test_ingests_from_payload_to_persistence_model(self):
        """Ensure one valid telemetry message is transformed and persisted correctly."""
        CapturingRepository.stored_readings.clear()

        bus = MessageBus()
        handler = TelemetryEventHandler(session_factory=FakeSession, repository_factory=CapturingRepository)
        bus.subscribe(TelemetryRecorded, handler)
        entrypoint = TelemetryEntrypoint(bus)

        message = {
            "header": {
                "type": "telemetry",
                "device_id": "esp32-greenhouse-a",
                "timestamp": "2026-04-04T12:34:56+00:00",
            },
            "payload": {
                "temperature": 25.5,
                "humidity": 60.0,
            },
        }

        await entrypoint.on_telemetry_message(
            topic="greenhouse/telemetry/esp32-greenhouse-a",
            payload=json.dumps(message).encode("utf-8"),
        )

        self.assertEqual(len(CapturingRepository.stored_readings), 1)
        reading = CapturingRepository.stored_readings[0]
        self.assertEqual(reading.device_id, "esp32-greenhouse-a")
        self.assertEqual(reading.temperature, 25.5)
        self.assertEqual(reading.humidity, 60.0)
        self.assertEqual(reading.timestamp.isoformat(), "2026-04-04T12:34:56+00:00")


if __name__ == "__main__":
    unittest.main()

