"""
Telemetry data models for the Smart Greenhouse system.

This module defines the data structures used to represent and persist
environmental sensor readings from greenhouse devices, as well as a
dead-letter table for messages that could not be fully processed.
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
        timestamp (datetime): UTC timestamp indicating when the reading was recorded.
            Defaults to the current UTC time if not explicitly set.
        device_id (str): Identifier for the physical device/sensor that generated
            this reading. Defaults to "strawberry_pi_01" (the primary greenhouse sensor).
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
    device_id: str = "strawberry_pi_01"


class FailedMessage(SQLModel, table=True):
    """
    Dead-letter record for MQTT messages that could not be fully processed.

    When a message fails at any stage (JSON decode, schema validation, or
    database persistence), its raw payload and the reason for the failure are
    stored here so that operators can inspect and replay them.

    Attributes:
        id (Optional[UUID]): Auto-generated primary key.
        topic (str): The MQTT topic the message arrived on.
        raw_payload (str): The raw message payload as a UTF-8 string (or the
            original bytes repr if decoding failed).
        failure_reason (str): Human-readable description of why the message failed.
        failed_at (datetime): UTC timestamp of when the failure was recorded.
    """

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    topic: str
    raw_payload: str
    failure_reason: str
    failed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
