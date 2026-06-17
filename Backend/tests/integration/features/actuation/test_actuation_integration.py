"""Integration tests for the actuation HTTP router.

Uses a real FastAPI app wired to a fake ActuationService to verify that the
HTTP transport layer (routing, serialisation, status codes) behaves correctly
without needing a live MQTT broker.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from features.actuation.models import ActuationAction, ActuationCommand
from features.actuation.router import router


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeActuationService:
    def __init__(self, ack_result: bool = True) -> None:
        self._ack_result = ack_result
        self.received_commands: list[ActuationCommand] = []

    async def publish_with_device_ack(self, command: ActuationCommand, timeout: float = 5.0) -> bool:
        self.received_commands.append(command)
        return self._ack_result

    def resolve_ack(self, command_id: str) -> bool:
        return False


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_app(service: Any | None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if service is not None:
        app.state.actuation_service = service
    return app


@pytest.fixture
def acking_service() -> FakeActuationService:
    return FakeActuationService(ack_result=True)


@pytest.fixture
def timing_out_service() -> FakeActuationService:
    return FakeActuationService(ack_result=False)


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_post_returns_200_and_accepted_when_device_acks(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actuation/esp32-greenhouse-a/command",
            json={"action": "PUMP_ON"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["device_id"] == "esp32-greenhouse-a"
    assert body["action"] == "PUMP_ON"
    assert "command_id" in body
    assert "timestamp" in body


async def test_post_forwards_parameters_to_service(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/actuation/esp32-greenhouse-b/command",
            json={"action": "PUMP_ON", "parameters": {"pulse_duration_ms": 500}},
        )

    assert len(acking_service.received_commands) == 1
    cmd = acking_service.received_commands[0]
    assert cmd.parameters == {"pulse_duration_ms": 500}
    assert cmd.device_id == "esp32-greenhouse-b"


async def test_post_accepts_all_valid_actions(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for action in ActuationAction:
            response = await client.post(
                "/api/v1/actuation/esp32-a/command",
                json={"action": action.value},
            )
            assert response.status_code == 200, f"Expected 200 for action {action.value}"


async def test_post_without_parameters_sends_none_to_service(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/actuation/esp32-c/command",
            json={"action": "FAN_ON"},
        )

    cmd = acking_service.received_commands[0]
    assert cmd.parameters is None


# ── Error paths ───────────────────────────────────────────────────────────────

async def test_post_returns_504_when_device_does_not_ack(timing_out_service) -> None:
    app = _make_app(timing_out_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actuation/esp32-greenhouse-a/command",
            json={"action": "PUMP_ON"},
        )

    assert response.status_code == 504
    assert "Timed out" in response.json()["detail"]


async def test_post_returns_503_when_actuation_service_is_not_configured() -> None:
    app = _make_app(service=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actuation/esp32-greenhouse-a/command",
            json={"action": "PUMP_ON"},
        )

    assert response.status_code == 503


async def test_post_returns_422_for_invalid_action_value(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actuation/esp32-greenhouse-a/command",
            json={"action": "SPIN_REALLY_FAST"},
        )

    assert response.status_code == 422


async def test_post_returns_422_when_action_is_missing(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actuation/esp32-greenhouse-a/command",
            json={},
        )

    assert response.status_code == 422


async def test_device_id_comes_from_path_not_body(acking_service) -> None:
    app = _make_app(acking_service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/actuation/path-device-id/command",
            json={"action": "FAN_OFF"},
        )

    cmd = acking_service.received_commands[0]
    assert cmd.device_id == "path-device-id"
