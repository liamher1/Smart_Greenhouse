from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from features.automation.models import PlantStage


class FruitRipenessDetected(BaseModel):
    """Published when the Raspberry Pi completes a YOLOv8 inference pass."""

    model_config = ConfigDict(frozen=True)

    device_id: str
    timestamp: datetime
    stage: PlantStage               # Dominant stage derived from highest percentage
    green_pct: float = Field(ge=0.0, le=100.0)
    white_pink_pct: float = Field(ge=0.0, le=100.0)
    red_pct: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
