"""Application service for actuation commands.

The service is intentionally thin: it translates the domain command into the
MQTT payload expected by the device and delegates the request-reply mechanics
to the shared `MqttDriver` infrastructure component.
"""

from __future__ import annotations

from typing import Any

from base.infrastructure.mqtt_driver import MqttDriver

from .models import ActuationCommand


class ActuationService:
	"""Publish actuation commands and resolve device acknowledgments."""

	def __init__(self, mqtt_driver: MqttDriver) -> None:
		"""Store the MQTT driver used to publish commands and resolve ACKs."""
		self._mqtt_driver = mqtt_driver

	async def publish_with_device_ack(self, command: ActuationCommand, timeout: float = 5.0) -> bool:
		"""Publish a command to the device topic and wait for an ACK.

		Args:
			command: Validated actuation command to publish.
			timeout: Maximum number of seconds to wait for the device reply.

		Returns:
			True if the device ACK arrives before the timeout, otherwise False.
		"""
		topic = f"commands/greenhouse/{command.device_id}"
		payload: dict[str, Any] = {
			"command_id": str(command.command_id),
			"device_id": command.device_id,
			"action": command.action.value,
			"timestamp": command.timestamp.isoformat(),
		}
		if command.parameters is not None:
			payload["parameters"] = command.parameters

		return await self._mqtt_driver.publish_with_device_ack(topic=topic, payload=payload, timeout=timeout)

	def resolve_ack(self, command_id: str) -> bool:
		"""Resolve a pending acknowledgment by command ID.

		Args:
			command_id: The identifier published with the original command.

		Returns:
			True when a matching pending ACK future was found and resolved.
		"""
		return self._mqtt_driver.resolve_ack(command_id)


