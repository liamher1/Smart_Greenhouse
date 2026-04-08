"""MQTT listeners for the actuation feature slice.

The ACK listener closes the request-reply loop by matching the device reply
back to the pending command future managed by the shared MQTT driver.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from .service import ActuationService


async def handle_ack_message(topic: str, payload: dict[str, Any], service: ActuationService) -> bool:
    """Resolve a pending command future when an ACK arrives from MQTT.

    Args:
        topic: MQTT topic used for the ACK message.
        payload: Decoded JSON payload from the device.
        service: Application service used to resolve the pending command.

    Returns:
        True when a matching pending command was found and resolved.
    """
    command_id = payload.get("command_id")
    if not command_id:
        logger.warning("Actuation ACK message missing command_id on topic {}", topic)
        return False

    return service.resolve_ack(str(command_id))


def register_actuation_ack_listener(mqtt_driver, service: ActuationService) -> None:
    """Register the MQTT callback that consumes device ACK messages.

    The listener subscribes to the wildcard topic pattern
    `commands/greenhouse/+/ack` so every device-specific ACK can be routed to
    the same command-resolution logic.
    """

    @mqtt_driver.on_message("commands/greenhouse/+/ack")
    async def on_ack(topic: str, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Failed to decode actuation ACK payload from topic {}", topic)
            return

        resolved = await handle_ack_message(topic=topic, payload=data, service=service)
        if not resolved:
            logger.warning("No pending actuation command found for ACK on topic {}", topic)
