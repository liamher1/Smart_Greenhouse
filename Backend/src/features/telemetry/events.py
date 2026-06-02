from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class TelemetryRecorded(BaseModel):
    """
    Domain event representing a new telemetry reading from a greenhouse device.

    This event is captured when a sensor sends updated environmental data.
    It is immutable (frozen) to ensure the integrity of the historical record.

    Attributes:
        temperature (float): The ambient temperature measured in Celsius.
        humidity (float): The relative humidity percentage (0-100).
        device_id (str): The unique hardware identifier of the ESP32/Sensor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature: float = Field(ge=-40.0, le=85.0)
    humidity: float = Field(ge=0.0, le=100.0)
    device_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    timestamp: datetime
    soil_moisture: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    water_level: Optional[int] = Field(default=None, ge=0, le=1)

