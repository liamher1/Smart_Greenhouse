"""
Telemetry data models for the Smart Greenhouse system.

This module defines the data structures used to represent and persist
environmental sensor readings from greenhouse devices.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class TelemetryReading(SQLModel, table=True):
    """
    Represents a single environmental telemetry reading from a greenhouse device.

    This model captures environmental metrics (temperature, humidity) along with
    metadata (timestamp, device identifier) for each sensor reading. It is designed
    to be persisted in a PostgreSQL database using SQLAlchemy ORM.

    Attributes:
        id (Optional[UUID]): Unique identifier for the telemetry reading.
            Auto-generated UUID if not provided. Primary key for database persistence.
        temperature (float): Temperature reading in Celsius from the greenhouse sensor.
        humidity (float): Humidity percentage (0-100) from the greenhouse sensor.
        timestamp (datetime): UTC timestamp from the originating device message.
            Defaults to the current UTC time only if not explicitly set.
        device_id (str): Identifier for the physical device/sensor that generated
            this reading.
    """

    # Unique identifier - automatically generated UUID, serves as primary key
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    # Environmental metrics
    temperature: float
    humidity: float

    # Metadata fields
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    device_id: str
