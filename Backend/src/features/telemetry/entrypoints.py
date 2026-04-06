"""Telemetry entrypoints for inbound MQTT messages."""
import json
from loguru import logger
from pydantic import ValidationError

from Backend.src.base.infrastructure.schemas import IncomingMqttDto
from Backend.src.base.infrastructure.message_bus import MessageBus
from Backend.src.features.telemetry.events import TelemetryRecorded

#test
class TelemetryEntrypoint:
    """
    Handles incoming telemetry messages from MQTT.
    """

    def __init__(self, message_bus: MessageBus):
        self._bus = message_bus

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
        try:
            # 1. & 2. Decode and Parse
            data = json.loads(payload.decode("utf-8"))

            # 3. Validate Envelope
            envelope = IncomingMqttDto(**data)

            # Verify message type (optional extra check)
            if envelope.header.type != "telemetry":
                logger.warning(f"Ignored message with type '{envelope.header.type}' on telemetry topic.")
                return

            # 4. Extract Payload
            payload_data = dict(envelope.payload)
            payload_data["device_id"] = envelope.header.device_id
            # Timestamp policy: use device timestamp from validated message header.
            payload_data["timestamp"] = envelope.header.timestamp

            # 5. Validate & Create Domain Event
            try:
                event = TelemetryRecorded(**payload_data)
            except ValidationError as e:
                logger.error(f"Telemetry payload validation failed: {str(e)}")
                return

            # 6. Dispatch
            logger.info(f"Dispatching TelemetryRecorded for {event.device_id}")
            await self._bus.handle(event)

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from topic {topic}")
        except ValidationError as e:
            logger.error(f"Schema validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error handling telemetry message: {str(e)}")


def register_telemetry_entrypoint(mqtt_driver, message_bus: MessageBus):
    """
    Registration helper to wire up the entrypoint with the adapter.
    This avoids global dependency injection issues.
    """
    entrypoint = TelemetryEntrypoint(message_bus)

    # Register with the decorator-like method
    # Effectively: @mqtt_driver.on_message("greenhouse/telemetry/+")
    mqtt_driver.on_message("greenhouse/telemetry/+")(entrypoint.on_telemetry_message)
    logger.info("Registered TelemetryEntrypoint handlers.")

