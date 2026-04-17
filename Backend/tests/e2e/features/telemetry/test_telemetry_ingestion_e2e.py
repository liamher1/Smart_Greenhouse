from __future__ import annotations

"""End-to-end telemetry ingestion test.

This module verifies the full MQTT-to-PostgreSQL path:
an external publisher sends a telemetry JSON payload to the broker,
the application's MQTT driver receives it, the telemetry entrypoint
creates a domain event, and the event handler persists the reading.
"""

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
import json
import sys

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from base.infrastructure.message_bus import MessageBus
from base.infrastructure.mqtt_driver import MqttDriver
from features.telemetry.entrypoints import register_telemetry_entrypoint
from features.telemetry.events import TelemetryRecorded
from features.telemetry.handlers import TelemetryEventHandler
from features.telemetry.models import TelemetryReading


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


@pytest.fixture(scope="module")
def require_optional_deps() -> None:
    """Skip this module when optional E2E runtime dependencies are missing.

    The test requires both `aiomqtt` for real MQTT publishing and
    `testcontainers` for spinning up ephemeral infrastructure.
    """
    pytest.importorskip("aiomqtt", reason="aiomqtt is required for MQTT E2E test")
    pytest.importorskip("testcontainers", reason="testcontainers is required for E2E test")


@pytest.fixture(scope="module")
def require_docker(require_optional_deps) -> None:
    """Skip the test if Docker is not available locally.

    `testcontainers` depends on a working Docker daemon, so this guard
    ensures the E2E test fails fast with a clear skip reason instead of
    producing container startup errors.
    """
    try:
        import docker
        from docker.errors import DockerException
    except ImportError as exc:
        docker = None  # type: ignore[assignment]
        DockerException = Exception  # type: ignore[assignment]
        pytest.skip(f"Docker SDK is required for E2E testcontainers tests: {exc}")

    client = None
    try:
        client = docker.from_env()
        client.ping()
    except DockerException as exc:
        pytest.skip(f"Docker is required for E2E testcontainers tests: {exc}")
    finally:
        if client is not None:
            client.close()


@pytest.fixture(scope="module")
def postgres_url(require_docker) -> str:
    """Start a disposable PostgreSQL container and yield its async URL.

    The fixture converts the synchronous testcontainer URL into an
    `asyncpg`-compatible SQLAlchemy connection string for the async test
    session factory.
    """
    from docker.errors import DockerException

    PostgresContainer = pytest.importorskip(
        "testcontainers.postgres",
        reason="testcontainers.postgres is required for E2E test",
    ).PostgresContainer

    try:
        with PostgresContainer("postgres:16") as postgres:
            sync_url = postgres.get_connection_url()
            yield (
                sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
                .replace("postgresql://", "postgresql+asyncpg://")
            )
    except DockerException as exc:
        pytest.skip(f"Postgres testcontainer could not start: {exc}")


@pytest.fixture(scope="module")
def mqtt_broker_endpoint(require_docker) -> tuple[str, int]:
    """Start a disposable Mosquitto container and yield its host/port.

    The returned endpoint is used by both the backend consumer and the
    external test publisher so the test exercises a real broker.
    """
    from docker.errors import DockerException

    DockerContainer = pytest.importorskip(
        "testcontainers.core.container",
        reason="testcontainers core container module is required for E2E test",
    ).DockerContainer

    command = (
        "sh -c \"printf 'listener 1883\\nallow_anonymous true\\n' "
        "> /tmp/mosquitto.conf && mosquitto -c /tmp/mosquitto.conf\""
    )

    container = None
    try:
        container = (
            DockerContainer("eclipse-mosquitto:2")
            .with_exposed_ports(1883)
            .with_command(command)
        )
        container.start()
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(1883))
        yield host, port
    except DockerException as exc:
        pytest.skip(f"Mosquitto testcontainer could not start: {exc}")
    finally:
        if container is not None:
            with suppress(Exception):
                container.stop()


@pytest.fixture
async def db_session_factory(postgres_url: str):
    """Create the async SQLAlchemy session factory for the test database.

    The fixture creates the schema before the test and drops it after the
    test so each run starts from a clean database state.
    """
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


async def test_mqtt_publish_is_ingested_and_saved_to_db(
    db_session_factory,
    mqtt_broker_endpoint: tuple[str, int],
) -> None:
    """Verify a real MQTT publish is consumed and persisted end to end.

    The test publishes a telemetry payload to the broker, waits for the
    background consumer to process it, and then checks the database for the
    persisted reading with the exact expected values.
    """
    aiomqtt = pytest.importorskip("aiomqtt", reason="aiomqtt is required for MQTT E2E test")

    broker_host, broker_port = mqtt_broker_endpoint

    bus = MessageBus()
    bus.subscribe(TelemetryRecorded, TelemetryEventHandler(session_factory=db_session_factory))

    mqtt_driver = MqttDriver(
        broker_url=broker_host,
        broker_port=broker_port,
        client_id="test-backend-consumer",
    )
    register_telemetry_entrypoint(mqtt_driver, bus)

    await mqtt_driver.connect()
    listener_task = asyncio.create_task(mqtt_driver.run())

    # Give the consumer loop a moment to subscribe before publishing.
    await asyncio.sleep(0.5)

    sent_timestamp = datetime(2026, 4, 7, 12, 50, tzinfo=timezone.utc)
    payload = {
        "header": {
            "type": "telemetry",
            "device_id": "esp32-greenhouse-e2e",
            "timestamp": sent_timestamp.isoformat(),
        },
        "payload": {
            "temperature": 25.5,
            "humidity": 60.0,
        },
    }

    try:
        async with aiomqtt.Client(
            hostname=broker_host,
            port=broker_port,
            identifier="test-external-publisher",
        ) as publisher:
            await publisher.publish(
                topic="greenhouse/telemetry/esp32-greenhouse-e2e",
                payload=json.dumps(payload),
                qos=1,
            )

        saved = None
        deadline = asyncio.get_running_loop().time() + 10.0
        while asyncio.get_running_loop().time() < deadline:
            async with db_session_factory() as session:
                result = await session.execute(
                    select(TelemetryReading).where(
                        TelemetryReading.device_id == "esp32-greenhouse-e2e"
                    )
                )
                saved = result.scalars().first()

            if saved is not None:
                break
            await asyncio.sleep(0.2)

        assert saved is not None, "Telemetry reading was not persisted within timeout"
        assert saved.temperature == 25.5
        assert saved.humidity == 60.0
        assert saved.device_id == "esp32-greenhouse-e2e"
        assert saved.timestamp == sent_timestamp
    finally:
        listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await listener_task
        await mqtt_driver.disconnect()
