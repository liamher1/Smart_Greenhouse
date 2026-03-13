"""
Event handlers for telemetry data in the Smart Greenhouse system.

This module defines the handlers that process telemetry-related domain events,
such as persisting new sensor readings to the database.
"""

from Backend.src.features.telemetry.events import TelemetryUpdatedEvent
from Backend.src.features.telemetry.models import TelemetryReading
from Backend.src.features.telemetry.repository import TelemetryRepository


class TelemetryEventHandler:
    """
    Handles domain events related to telemetry data.
    """

    def __init__(self, telemetry_repository: TelemetryRepository):
        """
        Initializes the handler with a telemetry repository.

        Args:
            telemetry_repository (TelemetryRepository): The repository for accessing telemetry data.
        """
        self.telemetry_repository = telemetry_repository

    async def __call__(self, event: TelemetryUpdatedEvent) -> None:
        """
        Handles the TelemetryUpdatedEvent by creating and saving a new telemetry reading.

        Args:
            event (TelemetryUpdatedEvent): The telemetry updated event to handle.
        """
        telemetry_reading = TelemetryReading(
            temperature=event.temperature,
            humidity=event.humidity,
            device_id=event.device_id,
        )
        await self.telemetry_repository.add_telemetry_reading(telemetry_reading)
