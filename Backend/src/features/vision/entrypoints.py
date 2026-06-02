from __future__ import annotations

import json

from loguru import logger
from pydantic import ValidationError

from base.infrastructure.message_bus import MessageBus
from base.infrastructure.schemas import IncomingMqttDto

from .events import FruitRipenessDetected


class VisionEntrypoint:
    def __init__(self, message_bus: MessageBus) -> None:
        self._bus = message_bus

    async def on_vision_message(self, topic: str, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
            envelope = IncomingMqttDto(**data)

            if envelope.header.type != "vision":
                logger.warning("[Vision] Ignored message with type '{}' on vision topic", envelope.header.type)
                return

            payload_data = dict(envelope.payload)
            payload_data["device_id"] = envelope.header.device_id
            payload_data["timestamp"] = envelope.header.timestamp

            event = FruitRipenessDetected(**payload_data)

        except json.JSONDecodeError:
            logger.error("[Vision] Failed to decode JSON from topic {}", topic)
            return
        except ValidationError as e:
            logger.error("[Vision] Schema validation failed: {}", e)
            return
        except Exception as e:
            logger.error("[Vision] Unexpected error on topic {}: {}", topic, e)
            return

        logger.info("[Vision] FruitRipenessDetected — device={} stage={}", event.device_id, event.stage)
        await self._bus.handle(event)


def register_vision_entrypoint(mqtt_driver, message_bus: MessageBus) -> None:
    entrypoint = VisionEntrypoint(message_bus)
    mqtt_driver.on_message("greenhouse/vision/+")(entrypoint.on_vision_message)
    logger.info("Registered VisionEntrypoint handler on greenhouse/vision/+")
