from datetime import datetime
from typing import Annotated

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

    # Wide operational range to support different greenhouse deployments.
    temperature: float = Field(ge=-40.0, le=85.0)
    humidity: float = Field(ge=0.0, le=100.0)
    device_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    # Device-reported timestamp from the MQTT message header.
    timestamp: datetime

