from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TelemetryReading


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

        Adds a new telemetry reading to the database session and flushes pending SQL.
        Transaction boundaries (commit/rollback) are managed by the caller.

        Args:
            telemetry_reading (TelemetryReading): The telemetry reading object to persist.

        Returns:
            None

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If a database error occurs during
                insertion or flush operations.

        Note:
            The provided telemetry_reading object is modified in-place to reflect
            any database-generated values (e.g., auto-generated UUID if not provided).
        """
        self.session.add(telemetry_reading)
        await self.session.flush()

    async def get_latest(self, device_id: str) -> TelemetryReading | None:
        result = await self.session.execute(
            select(TelemetryReading)
            .where(TelemetryReading.device_id == device_id)
            .order_by(desc(TelemetryReading.timestamp))
            .limit(1)
        )
        return result.scalars().first()

    async def get_history(self, device_id: str, limit: int = 50) -> list[TelemetryReading]:
        result = await self.session.execute(
            select(TelemetryReading)
            .where(TelemetryReading.device_id == device_id)
            .order_by(desc(TelemetryReading.timestamp))
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

