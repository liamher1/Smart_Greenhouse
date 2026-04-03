"""
Event handlers for telemetry data in the Smart Greenhouse system.

This module defines the handlers that process telemetry-related domain events,
such as persisting new sensor readings to the database.
"""

from typing import Optional
from loguru import logger

from Backend.src.features.telemetry.events import TelemetryRecorded
from Backend.src.features.telemetry.models import TelemetryReading
from Backend.src.features.telemetry.repository import TelemetryRepository
from Backend.src.features.telemetry.metrics import TelemetryMetrics


class TelemetryEventHandler:
    """
    Handles domain events related to telemetry data.
    """

    def __init__(
        self,
        telemetry_repository: TelemetryRepository,
        metrics: Optional[TelemetryMetrics] = None,
    ):
        """
        Initializes the handler with a telemetry repository and optional metrics.

        Args:
            telemetry_repository (TelemetryRepository): The repository for accessing telemetry data.
            metrics (TelemetryMetrics, optional): Shared metrics counters. If not
                provided a standalone instance is created.
        """
        self.telemetry_repository = telemetry_repository
        self._metrics = metrics or TelemetryMetrics()

    async def __call__(self, event: TelemetryRecorded) -> None:
        """
        Handles the TelemetryRecorded event by creating and saving a new telemetry reading.

        Args:
            event (TelemetryRecorded): The telemetry recorded event to handle.
        """
        telemetry_reading = TelemetryReading(
            temperature=event.temperature,
            humidity=event.humidity,
            device_id=event.device_id,
        )
        try:
            await self.telemetry_repository.add_telemetry_reading(telemetry_reading)
            self._metrics.increment_successful()
            logger.info(
                "Telemetry reading persisted",
                device_id=event.device_id,
                temperature=event.temperature,
                humidity=event.humidity,
            )
        except Exception as exc:
            self._metrics.increment_failed_persistence()
            logger.error(
                "Failed to persist telemetry reading",
                device_id=event.device_id,
                reason=str(exc),
            )
            raise
