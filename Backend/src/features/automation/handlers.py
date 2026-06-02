from __future__ import annotations

from typing import Callable

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from base.infrastructure.message_bus import MessageBus
from features.telemetry.events import TelemetryRecorded
from features.vision.events import FruitRipenessDetected

from .events import RuleTriggered
from .models import ControlRule, PlantStage
from .repository import AutomationRepository

_OPERATORS = {
    "lt":  lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
    "gt":  lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
}


def _evaluate(rule: ControlRule, event: TelemetryRecorded) -> bool:
    value = getattr(event, rule.sensor_metric, None)
    if value is None:
        return False
    op = _OPERATORS.get(rule.operator)
    if op is None:
        logger.warning("[Automation] Unknown operator '{}' in rule '{}'", rule.operator, rule.name)
        return False
    return op(value, rule.threshold)


class RipenessHandler:
    """Updates GreenhouseState when the Vision slice reports a new ripeness reading."""

    def __init__(self, session_factory: Callable[[], AsyncSession], bus: MessageBus) -> None:
        self._session_factory = session_factory

    async def __call__(self, event: FruitRipenessDetected) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                repo = AutomationRepository(session)
                await repo.upsert_greenhouse_state(event.device_id, event.stage)

        logger.info(
            "[Automation] GreenhouseState updated — device={} stage={}",
            event.device_id,
            event.stage,
        )


class TelemetryAutomationHandler:
    """Evaluates active ControlRules against incoming telemetry and fires RuleTriggered events."""

    def __init__(self, session_factory: Callable[[], AsyncSession], bus: MessageBus) -> None:
        self._session_factory = session_factory
        self._bus = bus

    async def __call__(self, event: TelemetryRecorded) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                repo = AutomationRepository(session)
                state = await repo.get_greenhouse_state(event.device_id)
                stage = state.plant_stage if state else PlantStage.GREEN
                rules = await repo.get_active_rules(stage)

        for rule in rules:
            if _evaluate(rule, event):
                triggered = RuleTriggered(
                    rule_id=rule.id,
                    device_id=rule.device_id,
                    action=rule.action,
                    pulse_duration_ms=rule.pulse_duration_ms,
                )
                logger.info(
                    "[Automation] Rule '{}' triggered — device={} action={}",
                    rule.name,
                    rule.device_id,
                    rule.action,
                )
                await self._bus.handle(triggered)
