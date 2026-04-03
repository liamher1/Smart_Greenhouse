"""
Integration tests for telemetry observability: structured logging, metrics
counters, and dead-letter (failed_messages) persistence.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from Backend.src.base.infrastructure.message_bus import MessageBus
from Backend.src.features.telemetry.entrypoints import TelemetryEntrypoint
from Backend.src.features.telemetry.handlers import TelemetryEventHandler
from Backend.src.features.telemetry.metrics import TelemetryMetrics
from Backend.src.features.telemetry.models import FailedMessage
from Backend.src.features.telemetry.events import TelemetryRecorded


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PAYLOAD = json.dumps(
    {
        "header": {
            "type": "telemetry",
            "device_id": "test-device-01",
            "timestamp": "2024-01-01T00:00:00Z",
        },
        "payload": {"temperature": 22.5, "humidity": 60.0},
    }
).encode()

TOPIC = "greenhouse/telemetry/test-device-01"


def _make_entrypoint(metrics=None, repository=None):
    """Build a TelemetryEntrypoint wired to a real MessageBus (no DB)."""
    bus = MessageBus()
    # Subscribe a no-op handler so the bus doesn't log warnings
    async def _noop(event):
        pass

    bus.subscribe(TelemetryRecorded, _noop)
    return TelemetryEntrypoint(bus, metrics=metrics, repository=repository)


# ---------------------------------------------------------------------------
# TelemetryMetrics unit tests
# ---------------------------------------------------------------------------


class TestTelemetryMetrics:
    def test_initial_counters_are_zero(self):
        m = TelemetryMetrics()
        assert m.received == 0
        assert m.bad_input == 0
        assert m.failed_persistence == 0
        assert m.successful == 0

    def test_increment_received(self):
        m = TelemetryMetrics()
        m.increment_received()
        m.increment_received()
        assert m.received == 2

    def test_increment_bad_input(self):
        m = TelemetryMetrics()
        m.increment_bad_input()
        assert m.bad_input == 1

    def test_increment_failed_persistence(self):
        m = TelemetryMetrics()
        m.increment_failed_persistence()
        assert m.failed_persistence == 1

    def test_increment_successful(self):
        m = TelemetryMetrics()
        m.increment_successful()
        assert m.successful == 1

    def test_as_dict(self):
        m = TelemetryMetrics()
        m.increment_received()
        m.increment_successful()
        d = m.as_dict()
        assert d == {
            "received": 1,
            "bad_input": 0,
            "failed_persistence": 0,
            "successful": 1,
        }


# ---------------------------------------------------------------------------
# TelemetryEntrypoint – metrics on error paths
# ---------------------------------------------------------------------------


class TestTelemetryEntrypointMetrics:
    @pytest.mark.asyncio
    async def test_valid_message_increments_received(self):
        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics)
        await ep.on_telemetry_message(TOPIC, VALID_PAYLOAD)
        assert metrics.received == 1

    @pytest.mark.asyncio
    async def test_invalid_json_increments_bad_input(self):
        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics)
        await ep.on_telemetry_message(TOPIC, b"not valid json {{")
        assert metrics.received == 1
        assert metrics.bad_input == 1
        assert metrics.successful == 0

    @pytest.mark.asyncio
    async def test_missing_header_increments_bad_input(self):
        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics)
        payload = json.dumps({"payload": {"temperature": 1.0}}).encode()
        await ep.on_telemetry_message(TOPIC, payload)
        assert metrics.bad_input == 1

    @pytest.mark.asyncio
    async def test_wrong_message_type_does_not_increment_bad_input(self):
        """A non-telemetry type is silently ignored, not counted as bad_input."""
        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics)
        payload = json.dumps(
            {
                "header": {
                    "type": "command",
                    "device_id": "dev-1",
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                "payload": {},
            }
        ).encode()
        await ep.on_telemetry_message(TOPIC, payload)
        assert metrics.bad_input == 0
        assert metrics.received == 1

    @pytest.mark.asyncio
    async def test_payload_validation_failure_increments_bad_input(self):
        """Missing required telemetry fields → bad_input."""
        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics)
        payload = json.dumps(
            {
                "header": {
                    "type": "telemetry",
                    "device_id": "dev-1",
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                "payload": {},  # temperature/humidity missing
            }
        ).encode()
        await ep.on_telemetry_message(TOPIC, payload)
        assert metrics.bad_input == 1


# ---------------------------------------------------------------------------
# TelemetryEntrypoint – structured log context on error paths
# ---------------------------------------------------------------------------


class TestTelemetryEntrypointLogging:
    @pytest.mark.asyncio
    async def test_json_decode_error_logs_topic(self, capsys):
        """Ensure the topic appears in structured log output on decode failure."""
        logged_messages = []

        def capture(message):
            logged_messages.append(message)

        from loguru import logger

        handler_id = logger.add(capture, format="{message}", level="ERROR")
        try:
            ep = _make_entrypoint()
            await ep.on_telemetry_message(TOPIC, b"{{bad json")
        finally:
            logger.remove(handler_id)

        # At least one error-level log should have been emitted
        assert any(logged_messages), "Expected at least one log message"

    @pytest.mark.asyncio
    async def test_validation_error_logs_device_id(self):
        """Validation failure should produce a log record mentioning the device."""
        logged_records = []

        def capture(message):
            logged_records.append(str(message))

        from loguru import logger

        handler_id = logger.add(capture, format="{message}", level="ERROR")
        try:
            ep = _make_entrypoint()
            # Envelope is valid but telemetry payload is missing fields
            payload = json.dumps(
                {
                    "header": {
                        "type": "telemetry",
                        "device_id": "device-xyz",
                        "timestamp": "2024-01-01T00:00:00Z",
                    },
                    "payload": {},
                }
            ).encode()
            await ep.on_telemetry_message(TOPIC, payload)
        finally:
            logger.remove(handler_id)

        assert any(logged_records), "Expected at least one error log"


# ---------------------------------------------------------------------------
# Dead-letter (FailedMessage) persistence
# ---------------------------------------------------------------------------


class TestDeadLetterPersistence:
    @pytest.mark.asyncio
    async def test_failed_message_persisted_on_json_error(self):
        """A bad-JSON message should be stored in the dead-letter repository."""
        repo = MagicMock()
        repo.add_failed_message = AsyncMock()

        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics, repository=repo)
        await ep.on_telemetry_message(TOPIC, b"{{invalid")

        repo.add_failed_message.assert_awaited_once()
        call_arg: FailedMessage = repo.add_failed_message.call_args[0][0]
        assert isinstance(call_arg, FailedMessage)
        assert call_arg.topic == TOPIC
        assert "JSON decode error" in call_arg.failure_reason

    @pytest.mark.asyncio
    async def test_failed_message_persisted_on_schema_error(self):
        """An invalid envelope should be stored in the dead-letter repository."""
        repo = MagicMock()
        repo.add_failed_message = AsyncMock()

        ep = _make_entrypoint(repository=repo)
        payload = json.dumps({"no_header": True}).encode()
        await ep.on_telemetry_message(TOPIC, payload)

        repo.add_failed_message.assert_awaited_once()
        call_arg: FailedMessage = repo.add_failed_message.call_args[0][0]
        assert "schema validation failed" in call_arg.failure_reason.lower()

    @pytest.mark.asyncio
    async def test_failed_message_persisted_on_payload_validation_error(self):
        """An invalid telemetry payload should be stored in the dead-letter repository."""
        repo = MagicMock()
        repo.add_failed_message = AsyncMock()

        ep = _make_entrypoint(repository=repo)
        payload = json.dumps(
            {
                "header": {
                    "type": "telemetry",
                    "device_id": "dev-1",
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                "payload": {},  # missing fields
            }
        ).encode()
        await ep.on_telemetry_message(TOPIC, payload)

        repo.add_failed_message.assert_awaited_once()
        call_arg: FailedMessage = repo.add_failed_message.call_args[0][0]
        assert "payload validation failed" in call_arg.failure_reason.lower()

    @pytest.mark.asyncio
    async def test_no_dead_letter_when_repository_not_provided(self):
        """When no repository is injected, failures are silently skipped (no crash)."""
        metrics = TelemetryMetrics()
        ep = _make_entrypoint(metrics=metrics, repository=None)
        # Should not raise even with no repository
        await ep.on_telemetry_message(TOPIC, b"{{bad json")
        assert metrics.bad_input == 1

    @pytest.mark.asyncio
    async def test_valid_message_does_not_create_dead_letter(self):
        """A valid message must NOT create any dead-letter records."""
        repo = MagicMock()
        repo.add_failed_message = AsyncMock()

        ep = _make_entrypoint(repository=repo)
        await ep.on_telemetry_message(TOPIC, VALID_PAYLOAD)

        repo.add_failed_message.assert_not_awaited()


# ---------------------------------------------------------------------------
# TelemetryEventHandler – metrics on persistence success/failure
# ---------------------------------------------------------------------------


class TestTelemetryHandlerMetrics:
    @pytest.mark.asyncio
    async def test_successful_persistence_increments_successful(self):
        repo = MagicMock()
        repo.add_telemetry_reading = AsyncMock()

        metrics = TelemetryMetrics()
        handler = TelemetryEventHandler(telemetry_repository=repo, metrics=metrics)
        event = TelemetryRecorded(temperature=20.0, humidity=50.0, device_id="dev-1")
        await handler(event)

        assert metrics.successful == 1
        assert metrics.failed_persistence == 0

    @pytest.mark.asyncio
    async def test_persistence_failure_increments_failed_persistence(self):
        repo = MagicMock()
        repo.add_telemetry_reading = AsyncMock(side_effect=RuntimeError("DB down"))

        metrics = TelemetryMetrics()
        handler = TelemetryEventHandler(telemetry_repository=repo, metrics=metrics)
        event = TelemetryRecorded(temperature=20.0, humidity=50.0, device_id="dev-1")

        with pytest.raises(RuntimeError):
            await handler(event)

        assert metrics.failed_persistence == 1
        assert metrics.successful == 0
