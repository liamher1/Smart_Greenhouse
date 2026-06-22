from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum
from sqlmodel import Field, SQLModel

from features.automation.models import PlantStage


class VisionReading(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    device_id: str = Field(index=True)
    stage: PlantStage = Field(sa_column=Column(SAEnum(PlantStage), nullable=False))
    green_pct: float
    white_pink_pct: float
    red_pct: float
    confidence: float
    image_filename: Optional[str] = Field(default=None)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
