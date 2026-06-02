"""Event handler that bridges the Automation Slice to the Actuation Slice.

RuleTriggeredHandler subscribes to RuleTriggered events and translates each
one into an ActuationCommand published over MQTT to the target device.
"""

from __future__ import annotations

from loguru import logger

from features.automation.events import RuleTriggered
from .models import ActuationAction, ActuationCommand
from .service import ActuationService


class RuleTriggeredHandler:
    """Publish an ActuationCommand to MQTT for every triggered ControlRule.

    If the action string in the event is not a valid ActuationAction the event
    is logged and dropped — this guards against stale rule data in the DB.
    """

    def __init__(self, actuation_service: ActuationService) -> None:
        self._service = actuation_service

    async def __call__(self, event: RuleTriggered) -> None:
        try:
            action = ActuationAction(event.action)
        except ValueError:
            logger.error(
                "[Actuation] Unknown action '{}' in RuleTriggered for rule={} — dropping.",
                event.action,
                event.rule_id,
            )
            return

        parameters = None
        if event.pulse_duration_ms > 0:
            parameters = {"pulse_duration_ms": event.pulse_duration_ms}

        command = ActuationCommand(
            device_id=event.device_id,
            action=action,
            parameters=parameters,
        )

        acked = await self._service.publish_with_device_ack(command)

        logger.info(
            "[Actuation] rule={} device={} action={} pulse={}ms ack={}",
            event.rule_id,
            event.device_id,
            action.value,
            event.pulse_duration_ms,
            acked,
        )
