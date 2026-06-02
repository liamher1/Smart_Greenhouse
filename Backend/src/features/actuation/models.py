"""Domain models for the actuation feature slice.

This module defines the command contract used to request device-level
actions over MQTT. The models are deliberately small and immutable so they
can be passed cleanly between the HTTP layer, application service, and MQTT
infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from base.domain.command import Command


class ActuationAction(str, Enum):
	"""Supported greenhouse actuation actions — values match firmware command strings."""

	PUMP_ON  = "PUMP_ON"
	PUMP_OFF = "PUMP_OFF"
	FAN_ON   = "FAN_ON"
	FAN_OFF  = "FAN_OFF"


@dataclass(frozen=True)
class ActuationCommand(Command[None]):
	"""Domain command representing one requested actuation operation.

	Attributes:
		device_id: Target device identifier that should receive the command.
		action: The requested actuation action.
		parameters: Optional free-form arguments for the device firmware.
		timestamp: UTC timestamp assigned when the command is created.
	"""

	device_id: str = ""
	action: ActuationAction = ActuationAction.PUMP_ON
	parameters: dict[str, Any] | None = None
	timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def __post_init__(self) -> None:
		"""Validate and normalize the command after dataclass creation."""
		self.validate()

	def validate(self) -> bool:
		"""Validate the command payload before it is published.

		Returns:
			True when the command is structurally valid.

		Raises:
			ValueError: If any required field is missing or malformed.
		"""
		if not self.device_id or not self.device_id.strip():
			raise ValueError("device_id must be a non-empty string")

		if not isinstance(self.action, ActuationAction):
			raise ValueError("action must be a valid ActuationAction")

		if self.parameters is not None and not isinstance(self.parameters, dict):
			raise ValueError("parameters must be a dictionary when provided")

		object.__setattr__(self, "device_id", self.device_id.strip())
		return True



