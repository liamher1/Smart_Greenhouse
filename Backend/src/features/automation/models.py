from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum
from sqlmodel import Field, SQLModel


class PlantStage(str, Enum):
    GREEN      = "Green"
    WHITE_PINK = "WhitePink"
    RED        = "Red"


class GreenhouseState(SQLModel, table=True):
    """Tracks the current ripeness stage for one greenhouse device."""

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    device_id: str = Field(index=True)
    plant_stage: PlantStage = Field(
        default=PlantStage.GREEN,
        sa_column=Column(SAEnum(PlantStage), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class WateringPolicy(SQLModel, table=True):
    """Per-stage operational targets used by the rules engine."""

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    plant_stage: PlantStage = Field(
        sa_column=Column(SAEnum(PlantStage), nullable=False, unique=True),
    )
    target_moisture: float = Field(description="Target soil moisture percentage 0–100")
    max_temperature: float = Field(description="Fan activates above this °C")
    is_active: bool = Field(default=True)


class ControlRule(SQLModel, table=True):
    """Generic threshold rule — evaluated against incoming telemetry events."""

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    name: str
    # NULL means the rule applies to every plant stage
    plant_stage: Optional[PlantStage] = Field(
        default=None,
        sa_column=Column(SAEnum(PlantStage), nullable=True),
    )
    # Name of the telemetry field to evaluate: temperature / humidity / soil_moisture
    sensor_metric: str
    # Comparison operator: lt | gt | lte | gte
    operator: str
    threshold: float
    # Value must be a valid ActuationAction string (PUMP_ON / PUMP_OFF / FAN_ON / FAN_OFF)
    action: str
    device_id: str
    # 0 means no firmware-level time limit
    pulse_duration_ms: int = Field(default=0)
    is_active: bool = Field(default=True)


class WateringTimes(SQLModel, table=True):
    """Per-stage watering schedule parameters."""

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    plant_stage: PlantStage = Field(
        sa_column=Column(SAEnum(PlantStage), nullable=False),
    )
    watering_duration_ms: int
    rest_period_sec: int
