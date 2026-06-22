from __future__ import annotations

from loguru import logger

from base.infrastructure.database import async_session_maker

from .events import FruitRipenessDetected
from .models import VisionReading
from .repository import VisionRepository


class VisionReadingHandler:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def handle(self, event: FruitRipenessDetected) -> None:
        reading = VisionReading(
            device_id=event.device_id,
            stage=event.stage,
            green_pct=event.green_pct,
            white_pink_pct=event.white_pink_pct,
            red_pct=event.red_pct,
            confidence=event.confidence,
            timestamp=event.timestamp,
        )
        async with self._session_factory() as session:
            async with session.begin():
                repo = VisionRepository(session)
                await repo.add(reading)
        logger.info("[Vision] Persisted VisionReading for device={} stage={}", event.device_id, event.stage)
