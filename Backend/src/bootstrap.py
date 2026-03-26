from __future__ import annotations

from functools import partial
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.infrastructure.database import async_session_maker, init_db
from src.base.infrastructure.message_bus import AsyncMessageBus
from src.features.telemetry.controllers import TelemetryController
from src.features.telemetry.handlers import handle_telemetry_recorded
from src.features.telemetry.repository import TelemetryRepository
from Backend.src.features.telemetry.events import TelemetryRecorded


class BootstrapContainer(TypedDict):
    controller: TelemetryController
    db_connection: AsyncSession


async def bootstrap_app() -> BootstrapContainer:
    await init_db()

    db_connection = async_session_maker()
    telemetry_repository = TelemetryRepository(db_connection)

    message_bus = AsyncMessageBus()
    telemetry_handler = partial(
        handle_telemetry_recorded,
        telemetry_repository=telemetry_repository,
    )
    message_bus.subscribe(TelemetryRecorded, telemetry_handler)

    controller = TelemetryController(message_bus)
    return {"controller": controller, "db_connection": db_connection}
