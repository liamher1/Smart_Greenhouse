"""
Telemetry Entrypoint.

This module is the bridge between the MQTT Infrastructure and the Telemetry Feature.
It defines the handler that receives raw MQTT messages, validates them against the
strict MessageEnvelope schema, and dispatches domain events.
"""
import json
from loguru import logger
from pydantic import ValidationError

from Backend.src.base.infrastructure.schemas import MessageEnvelope
from Backend.src.base.infrastructure.message_bus import MessageBus
from Backend.src.features.telemetry.events import TelemetryUpdatedEvent


class TelemetryEntrypoint:
    """
    Handles incoming telemetry messages from MQTT.
    """

    def __init__(self, message_bus: MessageBus):
        self._bus = message_bus

    async def handle_reading(self, topic: str, payload: bytes):
        """
        Process a raw MQTT message for telemetry.

        Steps:
        1. Decode bytes to string.
        2. Parse JSON.
        3. Validate against MessageEnvelope.
        4. Extract payload data.
        5. Create Domain Event.
        6. Dispatch to MessageBus.
        """
        try:
            # 1. & 2. Decode and Parse
            data = json.loads(payload.decode("utf-8"))
            
            # 3. Validate Envelope
            envelope = MessageEnvelope(**data)
            
            # Verify message type (optional extra check)
            if envelope.header.type != "telemetry":
                logger.warning(f"Ignored message with type '{envelope.header.type}' on telemetry topic.")
                return

            # 4. Extract Payload
            payload_data = envelope.payload

            # 5. Validate & Create Domain Event
            # Ensure required fields exist in the flexible payload
            if "temperature" not in payload_data or "humidity" not in payload_data:
                logger.error(f"Payload missing required fields: {payload_data}")
                return

            try:
                event = TelemetryUpdatedEvent(
                    temperature=float(payload_data["temperature"]),
                    humidity=float(payload_data["humidity"]),
                    device_id=envelope.header.device_id
                )
            except ValueError:
                logger.error(f"Invalid data types in payload: {payload_data}")
                return

            # 6. Dispatch
            logger.info(f"Dispatching TelemetryUpdatedEvent for {event.device_id}")
            await self._bus.handle(event)

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from topic {topic}")
        except ValidationError as e:
            logger.error(f"Schema validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error handling telemetry message: {str(e)}")


def register_entrypoints(adapter, message_bus: MessageBus):
    """
    Registration helper to wire up the entrypoint with the adapter.
    This avoids global dependency injection issues.
    """
    entrypoint = TelemetryEntrypoint(message_bus)
    
    # Register with the decorator-like method
    # Effectively: @adapter.on_message("greenhouse/telemetry/+")
    adapter.on_message("greenhouse/telemetry/+")(entrypoint.handle_reading)
    logger.info("Registered TelemetryEntrypoint handlers.")



