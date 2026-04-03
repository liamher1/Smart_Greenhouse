from sqlalchemy.ext.asyncio import AsyncSession
from Backend.src.features.telemetry.models import TelemetryReading, FailedMessage
from sqlalchemy import select


class TelemetryRepository:
    """
    Data access layer for greenhouse telemetry readings.

    The TelemetryRepository handles all database persistence logic for the greenhouse
    telemetry data. It follows the Repository Pattern to decouple data access from
    business logic for telemetry readings stored in the PostgreSQL database.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with an asynchronous database session.

        Dependency Injection is used here to allow the session to be managed
        at the caller or unit-of-work level.

        Args:
            session (AsyncSession): An asynchronous SQLAlchemy session instance
                responsible for managing database connections and transactions.

        Raises:
            TypeError: If session is not an AsyncSession instance.
        """
        self.session = session

    async def add_telemetry_reading(self, telemetry_reading: TelemetryReading) -> None:
        """
        Persist a new telemetry reading to the database.

        Adds a new telemetry reading to the database session, commits the transaction,
        and refreshes the object to populate database-generated fields like UUID and Timestamp.

        Args:
            telemetry_reading (TelemetryReading): The telemetry reading object to persist.

        Returns:
            None

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If a database error occurs during
                insertion, commit, or refresh operations.

        Note:
            The provided telemetry_reading object is modified in-place to reflect
            any database-generated values (e.g., auto-generated UUID if not provided).
        """
        # Stage the telemetry reading in the session for insertion
        self.session.add(telemetry_reading)
        # Commit the transaction to persist changes to the PostgreSQL database
        await self.session.commit()

        # Synchronize the Python object with the database record to ensure
        # it reflects any server-generated values (UUID, timestamp, etc.)
        await self.session.refresh(telemetry_reading)

    async def add_failed_message(self, failed_message: FailedMessage) -> None:
        """
        Persist a failed/dead-letter message record to the database.

        Args:
            failed_message (FailedMessage): The dead-letter record to persist.

        Returns:
            None

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If a database error occurs during
                insertion or commit.
        """
        self.session.add(failed_message)
        await self.session.commit()
        await self.session.refresh(failed_message)

