"""End-to-end actuation tests.

Exercises the full MQTT request-reply loop:
  HTTP POST → MQTT publish → device ACK on MQTT → HTTP 200 response.

Infrastructure: a disposable Mosquitto container (testcontainers) is spun up
so no external broker is required. A lightweight in-test "device simulator"
subscribes to the command topic and publishes the ACK automatically.
"""
from __future__ import annotations

import asyncio
import json
import sys
from contextlib import suppress

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from base.infrastructure.mqtt_driver import MqttDriver
from features.actuation.listeners import register_actuation_ack_listener
from features.actuation.router import router
from features.actuation.service import ActuationService


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]

DEVICE_ID = "esp32-greenhouse-e2e-act"


# ── Guards ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def require_optional_deps() -> None:
    pytest.importorskip("aiomqtt", reason="aiomqtt is required for actuation E2E test")
    pytest.importorskip("testcontainers", reason="testcontainers is required for actuation E2E test")


@pytest.fixture(scope="module")
def require_docker(require_optional_deps) -> None:
    try:
        import docker
        from docker.errors import DockerException
    except ImportError as exc:
        pytest.skip(f"Docker SDK is required for E2E testcontainers tests: {exc}")

    client = None
    try:
        client = docker.from_env()
        client.ping()
    except Exception as exc:
        pytest.skip(f"Docker is required for E2E testcontainers tests: {exc}")
    finally:
        if client is not None:
            client.close()


# ── Infrastructure fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mqtt_broker_endpoint(require_docker) -> tuple[str, int]:
    """Start a disposable Mosquitto container and yield its host/port."""
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


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _run_device_simulator(
    broker_host: str,
    broker_port: int,
    device_id: str,
    ready_event: asyncio.Event,
    stop_event: asyncio.Event,
) -> None:
    """Subscribe to the device command topic and auto-reply with an ACK.

    Signals *ready_event* once subscribed so the test knows it is safe to POST.
    Exits when *stop_event* is set or when it has replied to one command.
    """
    aiomqtt = pytest.importorskip("aiomqtt")

    async with aiomqtt.Client(
        hostname=broker_host,
        port=broker_port,
        identifier=f"test-device-{device_id}",
    ) as client:
        await client.subscribe(f"commands/greenhouse/{device_id}")
        ready_event.set()

        async for message in client.messages:
            if stop_event.is_set():
                break
            try:
                data = json.loads(message.payload.decode("utf-8"))
                command_id = data.get("command_id")
                if command_id:
                    ack_topic = f"commands/greenhouse/{device_id}/ack"
                    await client.publish(
                        ack_topic,
                        json.dumps({"command_id": command_id}),
                        qos=1,
                    )
            except Exception:
                pass
            break  # one command per test


# ── Tests ──────────────────────────────────────────────────────────────────────

async def test_actuation_command_reaches_device_and_returns_200(
    mqtt_broker_endpoint: tuple[str, int],
) -> None:
    """POST a command, have the simulated device ACK it, expect HTTP 200."""
    broker_host, broker_port = mqtt_broker_endpoint

    mqtt_driver = MqttDriver(
        broker_url=broker_host,
        broker_port=broker_port,
        client_id="test-backend-actuation-e2e",
    )
    service = ActuationService(mqtt_driver=mqtt_driver)
    register_actuation_ack_listener(mqtt_driver, service)

    await mqtt_driver.connect()
    listener_task = asyncio.create_task(mqtt_driver.run())
    await asyncio.sleep(0.3)  # let listener subscribe

    app = FastAPI()
    app.include_router(router)
    app.state.actuation_service = service

    device_ready = asyncio.Event()
    stop_event = asyncio.Event()
    device_task = asyncio.create_task(
        _run_device_simulator(broker_host, broker_port, DEVICE_ID, device_ready, stop_event)
    )
    await asyncio.wait_for(device_ready.wait(), timeout=5.0)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/actuation/{DEVICE_ID}/command",
                json={"action": "PUMP_ON"},
                timeout=10.0,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "accepted"
        assert body["device_id"] == DEVICE_ID
        assert body["action"] == "PUMP_ON"
        assert "command_id" in body
    finally:
        stop_event.set()
        listener_task.cancel()
        device_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await listener_task
        with suppress(asyncio.CancelledError, Exception):
            await device_task
        await mqtt_driver.disconnect()


async def test_actuation_command_with_parameters_reaches_device(
    mqtt_broker_endpoint: tuple[str, int],
) -> None:
    """Parameters included in the POST body are forwarded in the MQTT payload."""
    broker_host, broker_port = mqtt_broker_endpoint

    mqtt_driver = MqttDriver(
        broker_url=broker_host,
        broker_port=broker_port,
        client_id="test-backend-actuation-params-e2e",
    )
    service = ActuationService(mqtt_driver=mqtt_driver)
    register_actuation_ack_listener(mqtt_driver, service)

    await mqtt_driver.connect()
    listener_task = asyncio.create_task(mqtt_driver.run())
    await asyncio.sleep(0.3)

    received_payloads: list[dict] = []

    async def capturing_simulator() -> None:
        aiomqtt = pytest.importorskip("aiomqtt")
        async with aiomqtt.Client(
            hostname=broker_host,
            port=broker_port,
            identifier="test-device-params-capture",
        ) as client:
            await client.subscribe(f"commands/greenhouse/{DEVICE_ID}-params")
            async for message in client.messages:
                data = json.loads(message.payload.decode("utf-8"))
                received_payloads.append(data)
                ack_topic = f"commands/greenhouse/{DEVICE_ID}-params/ack"
                await client.publish(
                    ack_topic,
                    json.dumps({"command_id": data.get("command_id")}),
                    qos=1,
                )
                break

    device_task = asyncio.create_task(capturing_simulator())
    await asyncio.sleep(0.3)  # let device subscribe

    app = FastAPI()
    app.include_router(router)
    app.state.actuation_service = service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/actuation/{DEVICE_ID}-params/command",
                json={"action": "PUMP_ON", "parameters": {"pulse_duration_ms": 400}},
                timeout=10.0,
            )

        assert response.status_code == 200
        assert len(received_payloads) == 1
        payload = received_payloads[0]
        assert payload["action"] == "PUMP_ON"
        assert payload["parameters"] == {"pulse_duration_ms": 400}
        assert payload["device_id"] == f"{DEVICE_ID}-params"
    finally:
        listener_task.cancel()
        device_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await listener_task
        with suppress(asyncio.CancelledError, Exception):
            await device_task
        await mqtt_driver.disconnect()


async def test_actuation_returns_504_when_no_device_responds(
    mqtt_broker_endpoint: tuple[str, int],
) -> None:
    """When no device ACKs the command, the service times out and HTTP returns 504."""
    broker_host, broker_port = mqtt_broker_endpoint

    mqtt_driver = MqttDriver(
        broker_url=broker_host,
        broker_port=broker_port,
        client_id="test-backend-actuation-timeout-e2e",
    )
    service = ActuationService(mqtt_driver=mqtt_driver)
    register_actuation_ack_listener(mqtt_driver, service)

    await mqtt_driver.connect()
    listener_task = asyncio.create_task(mqtt_driver.run())
    await asyncio.sleep(0.3)

    app = FastAPI()
    app.include_router(router)
    app.state.actuation_service = service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/actuation/{DEVICE_ID}-silent/command",
                json={"action": "FAN_ON"},
                timeout=15.0,
            )

        assert response.status_code == 504
        assert "Timed out" in response.json()["detail"]
    finally:
        listener_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await listener_task
        await mqtt_driver.disconnect()
