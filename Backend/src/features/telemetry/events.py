from pydantic import BaseModel, ConfigDict


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

    temperature: float
    humidity: float
    device_id: str

