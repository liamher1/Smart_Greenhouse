from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer

from features.telemetry.events import TelemetryRecorded
from features.telemetry.handlers import TelemetryEventHandler
from features.telemetry.models import TelemetryReading
from features.telemetry.repository import TelemetryRepository


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.fixture(scope="module")
def postgres_url() -> str:
    with PostgresContainer("postgres:16") as postgres:
        sync_url = postgres.get_connection_url()
        yield (
            sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
            .replace("postgresql://", "postgresql+asyncpg://")
        )


@pytest.fixture
async def db_session_factory(postgres_url: str):
    engine = create_async_engine(postgres_url, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    try:
        yield session_factory
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        await engine.dispose()


async def test_handler_persists_telemetry_to_real_postgres(db_session_factory) -> None:
    handler = TelemetryEventHandler(
        session_factory=db_session_factory,
        repository_factory=TelemetryRepository,
    )

    event = TelemetryRecorded(
        temperature=26.1,
        humidity=64.2,
        device_id="esp32-greenhouse-int",
        timestamp=datetime(2026, 4, 7, 12, 40, tzinfo=timezone.utc),
    )

    await handler(event)

    async with db_session_factory() as session:
        result = await session.execute(
            select(TelemetryReading).where(TelemetryReading.device_id == event.device_id)
        )
        saved = result.scalars().all()

    assert len(saved) == 1
    row = saved[0]
    assert row.temperature == event.temperature
    assert row.humidity == event.humidity
    assert row.device_id == event.device_id
    assert row.timestamp == event.timestamp
    assert row.id is not None
