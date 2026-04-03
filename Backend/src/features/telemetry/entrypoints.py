"""Telemetry entrypoints for inbound MQTT messages."""
import json
from typing import Optional
from loguru import logger
from pydantic import ValidationError

from Backend.src.base.infrastructure.schemas import IncomingMqttDto
from Backend.src.base.infrastructure.message_bus import MessageBus
from Backend.src.features.telemetry.events import TelemetryRecorded
from Backend.src.features.telemetry.metrics import TelemetryMetrics
from Backend.src.features.telemetry.models import FailedMessage


class TelemetryEntrypoint:
    """
    Handles incoming telemetry messages from MQTT.
    """

    def __init__(
        self,
        message_bus: MessageBus,
        metrics: Optional[TelemetryMetrics] = None,
        repository=None,
    ):
        self._bus = message_bus
        self._metrics = metrics or TelemetryMetrics()
        self._repository = repository

    async def on_telemetry_message(self, topic: str, payload: bytes):
        """
        Process a raw MQTT message for telemetry.

        Steps:
        1. Decode bytes to string.
        2. Parse JSON.
        3. Validate against IncomingMqttDto.
        4. Extract payload data.
        5. Create Domain Event.
        6. Dispatch to MessageBus.
        """
        self._metrics.increment_received()
        raw_payload_str: str = ""

        try:
            # 1. & 2. Decode and Parse
            try:
                raw_payload_str = payload.decode("utf-8")
                data = json.loads(raw_payload_str)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                reason = f"JSON decode error: {exc}"
                logger.error(
                    "Failed to decode JSON payload",
                    topic=topic,
                    reason=reason,
                )
                self._metrics.increment_bad_input()
                await self._persist_failed_message(topic, raw_payload_str or repr(payload), reason)
                return

            # 3. Validate Envelope
            try:
                envelope = IncomingMqttDto(**data)
            except ValidationError as exc:
                reason = f"Envelope schema validation failed: {exc}"
                logger.error(
                    "MQTT envelope validation failed",
                    topic=topic,
                    reason=reason,
                )
                self._metrics.increment_bad_input()
                await self._persist_failed_message(topic, raw_payload_str, reason)
                return

            device_id = envelope.header.device_id

            # Verify message type (optional extra check)
            if envelope.header.type != "telemetry":
                logger.warning(
                    "Ignored message with unexpected type",
                    topic=topic,
                    device_id=device_id,
                    message_type=envelope.header.type,
                )
                return

            # 4. Extract Payload
            payload_data = dict(envelope.payload)
            payload_data["device_id"] = device_id

            # 5. Validate & Create Domain Event
            try:
                event = TelemetryRecorded(**payload_data)
            except ValidationError as exc:
                reason = f"Telemetry payload validation failed: {exc}"
                logger.error(
                    "Telemetry payload validation failed",
                    topic=topic,
                    device_id=device_id,
                    reason=reason,
                )
                self._metrics.increment_bad_input()
                await self._persist_failed_message(topic, raw_payload_str, reason)
                return

            # 6. Dispatch
            logger.info(
                "Dispatching TelemetryRecorded",
                topic=topic,
                device_id=event.device_id,
            )
            await self._bus.handle(event)

        except Exception as exc:
            logger.error(
                "Unexpected error handling telemetry message",
                topic=topic,
                reason=str(exc),
            )

    async def _persist_failed_message(
        self, topic: str, raw_payload: str, reason: str
    ) -> None:
        """Persist a dead-letter record if a repository is available."""
        if self._repository is None:
            return
        try:
            record = FailedMessage(
                topic=topic,
                raw_payload=raw_payload,
                failure_reason=reason,
            )
            await self._repository.add_failed_message(record)
            logger.debug(
                "Dead-letter record persisted",
                topic=topic,
                reason=reason,
            )
        except Exception as exc:
            logger.error(
                "Failed to persist dead-letter record",
                topic=topic,
                reason=str(exc),
            )


def register_telemetry_entrypoint(
    mqtt_driver,
    message_bus: MessageBus,
    metrics: Optional[TelemetryMetrics] = None,
    repository=None,
):
    """
    Registration helper to wire up the entrypoint with the adapter.
    This avoids global dependency injection issues.
    """
    entrypoint = TelemetryEntrypoint(message_bus, metrics=metrics, repository=repository)

    # Register with the decorator-like method
    # Effectively: @mqtt_driver.on_message("greenhouse/telemetry/+")
    mqtt_driver.on_message("greenhouse/telemetry/+")(entrypoint.on_telemetry_message)
    logger.info("Registered TelemetryEntrypoint handlers.")

