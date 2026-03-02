from datetime import datetime , timezone
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class TelemetryReading(SQLModel, table=True):
    id : Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    temperature : float
    humidity : float

    timestamp : datetime = Field(
        default_factory = lambda: datetime.now(timezone.utc)
    )
    device_id : str = "strawberry_pi_01"