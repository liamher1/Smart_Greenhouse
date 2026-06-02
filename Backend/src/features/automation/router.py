from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from base.infrastructure.database import get_session

from .models import ControlRule, GreenhouseState, PlantStage, WateringPolicy

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


# ── Request / response schemas ────────────────────────────────────────────────

class ControlRuleCreate(BaseModel):
    name: str
    plant_stage: Optional[PlantStage] = None
    sensor_metric: str
    operator: str
    threshold: float
    action: str
    device_id: str
    pulse_duration_ms: int = 0


class ControlRulePatch(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    threshold: Optional[float] = None
    pulse_duration_ms: Optional[int] = None


class WateringPolicyUpsert(BaseModel):
    plant_stage: PlantStage
    target_moisture: float
    max_temperature: float
    is_active: bool = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/state", status_code=status.HTTP_200_OK)
async def get_state(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    result = await session.execute(select(GreenhouseState))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "device_id": r.device_id,
            "plant_stage": r.plant_stage,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@router.get("/rules", status_code=status.HTTP_200_OK)
async def list_rules(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    result = await session.execute(select(ControlRule))
    return [r.model_dump() for r in result.scalars().all()]


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: ControlRuleCreate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rule = ControlRule(**body.model_dump())
    session.add(rule)
    await session.flush()
    return rule.model_dump()


@router.patch("/rules/{rule_id}", status_code=status.HTTP_200_OK)
async def patch_rule(
    rule_id: UUID,
    body: ControlRulePatch,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    result = await session.execute(select(ControlRule).where(ControlRule.id == rule_id))
    rule = result.scalars().first()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)

    await session.flush()
    return rule.model_dump()


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(select(ControlRule).where(ControlRule.id == rule_id))
    rule = result.scalars().first()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await session.delete(rule)


@router.get("/policies", status_code=status.HTTP_200_OK)
async def list_policies(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    result = await session.execute(select(WateringPolicy))
    return [r.model_dump() for r in result.scalars().all()]


@router.post("/policies", status_code=status.HTTP_201_CREATED)
async def upsert_policy(
    body: WateringPolicyUpsert,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    result = await session.execute(
        select(WateringPolicy).where(WateringPolicy.plant_stage == body.plant_stage)
    )
    policy = result.scalars().first()
    if policy is None:
        policy = WateringPolicy(**body.model_dump())
        session.add(policy)
    else:
        for field, value in body.model_dump().items():
            setattr(policy, field, value)

    await session.flush()
    return policy.model_dump()
