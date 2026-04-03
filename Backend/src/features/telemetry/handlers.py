"""
Event handlers for telemetry data in the Smart Greenhouse system.

This module defines the handlers that process telemetry-related domain events,
such as persisting new sensor readings to the database.
"""

from typing import Callable
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.src.features.telemetry.events import TelemetryRecorded
from Backend.src.features.telemetry.models import TelemetryReading
from Backend.src.features.telemetry.repository import TelemetryRepository


class TelemetryEventHandler:
    """
    Handles domain events related to telemetry data.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        repository_factory: Callable[[AsyncSession], TelemetryRepository] = TelemetryRepository,
    ):
        """
        Initializes the handler with a telemetry repository.

        Args:
            session_factory (Callable[[], AsyncSession]): Factory that returns
                a fresh AsyncSession for each inbound message.
            repository_factory (Callable[[AsyncSession], TelemetryRepository]):
                Factory for constructing repositories bound to the current session.
        """
        self._session_factory = session_factory
        self._repository_factory = repository_factory

    async def __call__(self, event: TelemetryRecorded) -> None:
        """
        Handles the TelemetryRecorded event by creating and saving a new telemetry reading.

        Args:
            event (TelemetryRecorded): The telemetry recorded event to handle.
        """


        # Create a fresh DB session for this single inbound event/message.
        # The context manager guarantees session cleanup (close) when done.
        async with self._session_factory() as session:
            try:
                # Open a transaction boundary for all DB work in this block.
                # If no exception occurs, this context commits automatically.
                async with session.begin():
                    # Build a repository bound to the current session (unit-of-work scope).
                    telemetry_repository = self._repository_factory(session)

                    # Translate the domain event into a persistence model.
                    telemetry_reading = TelemetryReading(
                        temperature=event.temperature,
                        humidity=event.humidity,
                        device_id=event.device_id,
                    )

                    # Stage + flush the reading through repository logic.
                    await telemetry_repository.add_telemetry_reading(telemetry_reading)
            except Exception:
                # Defensive rollback in case the transaction is still active.
                if session.in_transaction():
                    await session.rollback()

                # Log the full stack trace for observability/troubleshooting.
                logger.exception("Failed to persist telemetry event; transaction rolled back.")
                # Re-raise so upstream layers (bus/retry/monitoring) can handle failure.
                raise
