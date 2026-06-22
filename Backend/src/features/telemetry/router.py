from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from base.infrastructure.database import get_session

from .repository import TelemetryRepository

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


@router.get("/latest/{device_id}", status_code=status.HTTP_200_OK)
async def get_latest(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = TelemetryRepository(session)
    reading = await repo.get_latest(device_id)
    if reading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No readings found")
    return {
        "id": str(reading.id),
        "device_id": reading.device_id,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "soil_moisture": reading.soil_moisture,
        "water_level": reading.water_level,
        "timestamp": reading.timestamp.isoformat(),
    }


@router.get("/history/{device_id}", status_code=status.HTTP_200_OK)
async def get_history(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    repo = TelemetryRepository(session)
    readings = await repo.get_history(device_id, limit)
    return [
        {
            "id": str(r.id),
            "device_id": r.device_id,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "soil_moisture": r.soil_moisture,
            "water_level": r.water_level,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in readings
    ]
