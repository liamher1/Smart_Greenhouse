from sqlalchemy.ext.asyncio import AsyncSession
from Backend.src.features.telemetry.models import TelemetryReading
from sqlalchemy import select
class TelemetryRepository:
    """
    The TelemetryRepository handles all database persistence logic
    for the greenhouse telemetry data. It follows the Repository Pattern
    to decouple data access from business handlers.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the repository with an asynchronous database session.
        Dependency Injection is used here to allow the session to be managed
        at the caller or unit-of-work level.
        """
        self.session = session
    async def add_telemetry_reading(self, telemetry_reading: TelemetryReading):
        """
        Adds a new telemetry reading to the database session, commits the transaction,
        and refreshes the object to populate database-generated fields like UUID and Timestamp."""
        # Add the object to the session staging area
        self.session.add(telemetry_reading)
        # Commit the changes to the PostgreSQL database
        await self.session.commit()
        # Sync the Python object with the record created in DB
        await self.session.refresh(telemetry_reading)

