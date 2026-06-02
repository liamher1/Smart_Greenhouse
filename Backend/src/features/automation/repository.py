from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ControlRule, GreenhouseState, PlantStage, WateringPolicy


class AutomationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_greenhouse_state(self, device_id: str) -> Optional[GreenhouseState]:
        result = await self._session.execute(
            select(GreenhouseState).where(GreenhouseState.device_id == device_id)
        )
        return result.scalars().first()

    async def upsert_greenhouse_state(self, device_id: str, stage: PlantStage) -> GreenhouseState:
        state = await self.get_greenhouse_state(device_id)
        if state is None:
            state = GreenhouseState(device_id=device_id, plant_stage=stage)
            self._session.add(state)
        else:
            state.plant_stage = stage
            state.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return state

    async def get_active_rules(self, stage: PlantStage) -> list[ControlRule]:
        """Return rules that are active and scoped to this stage or all stages (NULL)."""
        result = await self._session.execute(
            select(ControlRule).where(
                ControlRule.is_active == True,  # noqa: E712
                or_(ControlRule.plant_stage == stage, ControlRule.plant_stage == None),  # noqa: E711
            )
        )
        return list(result.scalars().all())

    async def get_policy(self, stage: PlantStage) -> Optional[WateringPolicy]:
        result = await self._session.execute(
            select(WateringPolicy).where(
                WateringPolicy.plant_stage == stage,
                WateringPolicy.is_active == True,  # noqa: E712
            )
        )
        return result.scalars().first()
