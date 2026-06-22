from __future__ import annotations

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .models import VisionReading


class VisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, reading: VisionReading) -> None:
        self._session.add(reading)
        await self._session.flush()

    async def get_latest(self, device_id: str) -> VisionReading | None:
        result = await self._session.execute(
            select(VisionReading)
            .where(VisionReading.device_id == device_id)
            .order_by(desc(VisionReading.timestamp))
            .limit(1)
        )
        return result.scalars().first()
