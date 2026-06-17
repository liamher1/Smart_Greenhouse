"""Unit tests for the actuation feature slice.

Tests cover:
- ActuationCommand model validation
- ActuationService payload construction and driver delegation
- handle_ack_message listener logic
- RuleTriggeredHandler event-to-command mapping
"""
from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest

from features.actuation.handlers import RuleTriggeredHandler
from features.actuation.listeners import handle_ack_message
from features.actuation.models import ActuationAction, ActuationCommand
from features.actuation.service import ActuationService
from features.automation.events import RuleTriggered


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeMqttDriver:
    def __init__(self, ack_result: bool = True) -> None:
        self.published_calls: list[tuple[str, dict]] = []
        self._ack_result = ack_result
        self.resolve_calls: list[str] = []

    async def publish_with_device_ack(self, topic: str, payload: dict, timeout: float = 5.0) -> bool:
        self.published_calls.append((topic, dict(payload)))
        return self._ack_result

    def resolve_ack(self, command_id: str) -> bool:
        self.resolve_calls.append(command_id)
        return self._ack_result


class FakeActuationService:
    def __init__(self, resolve_result: bool = True) -> None:
        self._resolve_result = resolve_result
        self.resolve_calls: list[str] = []
        self.publish_calls: list[ActuationCommand] = []

    async def publish_with_device_ack(self, command: ActuationCommand, timeout: float = 5.0) -> bool:
        self.publish_calls.append(command)
        return self._resolve_result

    def resolve_ack(self, command_id: str) -> bool:
        self.resolve_calls.append(command_id)
        return self._resolve_result


# ── ActuationCommand validation ───────────────────────────────────────────────

def test_valid_command_creates_successfully() -> None:
    cmd = ActuationCommand(device_id="esp32-a", action=ActuationAction.PUMP_ON)
    assert cmd.device_id == "esp32-a"
    assert cmd.action == ActuationAction.PUMP_ON
    assert isinstance(cmd.command_id, UUID)


def test_empty_device_id_raises() -> None:
    with pytest.raises(ValueError, match="device_id"):
        ActuationCommand(device_id="", action=ActuationAction.FAN_ON)


def test_whitespace_only_device_id_raises() -> None:
    with pytest.raises(ValueError, match="device_id"):
        ActuationCommand(device_id="   ", action=ActuationAction.PUMP_OFF)


def test_device_id_is_stripped_of_whitespace() -> None:
    cmd = ActuationCommand(device_id="  esp32-b  ", action=ActuationAction.FAN_OFF)
    assert cmd.device_id == "esp32-b"


def test_parameters_must_be_dict_when_provided() -> None:
    with pytest.raises(ValueError, match="parameters"):
        ActuationCommand(device_id="esp32-a", action=ActuationAction.PUMP_ON, parameters="bad")  # type: ignore[arg-type]


def test_none_parameters_is_valid() -> None:
    cmd = ActuationCommand(device_id="esp32-a", action=ActuationAction.PUMP_ON, parameters=None)
    assert cmd.parameters is None


def test_dict_parameters_are_valid() -> None:
    cmd = ActuationCommand(
        device_id="esp32-a",
        action=ActuationAction.PUMP_ON,
        parameters={"pulse_ms": 500},
    )
    assert cmd.parameters == {"pulse_ms": 500}


def test_each_command_has_unique_id() -> None:
    cmd1 = ActuationCommand(device_id="dev-1", action=ActuationAction.FAN_ON)
    cmd2 = ActuationCommand(device_id="dev-1", action=ActuationAction.FAN_ON)
    assert cmd1.command_id != cmd2.command_id


def test_all_action_variants_are_accepted() -> None:
    for action in ActuationAction:
        cmd = ActuationCommand(device_id="esp32-a", action=action)
        assert cmd.action == action


# ── ActuationService ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_service_publishes_to_correct_topic() -> None:
    driver = FakeMqttDriver(ack_result=True)
    service = ActuationService(mqtt_driver=driver)
    command = ActuationCommand(device_id="esp32-c", action=ActuationAction.PUMP_ON)

    await service.publish_with_device_ack(command)

    assert len(driver.published_calls) == 1
    topic, _ = driver.published_calls[0]
    assert topic == "commands/greenhouse/esp32-c"


@pytest.mark.asyncio
async def test_service_includes_required_fields_in_payload() -> None:
    driver = FakeMqttDriver()
    service = ActuationService(mqtt_driver=driver)
    command = ActuationCommand(device_id="esp32-d", action=ActuationAction.FAN_ON)

    await service.publish_with_device_ack(command)

    _, payload = driver.published_calls[0]
    assert payload["command_id"] == str(command.command_id)
    assert payload["device_id"] == "esp32-d"
    assert payload["action"] == "FAN_ON"
    assert "timestamp" in payload


@pytest.mark.asyncio
async def test_service_includes_parameters_when_present() -> None:
    driver = FakeMqttDriver()
    service = ActuationService(mqtt_driver=driver)
    command = ActuationCommand(
        device_id="esp32-e",
        action=ActuationAction.PUMP_ON,
        parameters={"pulse_duration_ms": 300},
    )

    await service.publish_with_device_ack(command)

    _, payload = driver.published_calls[0]
    assert payload["parameters"] == {"pulse_duration_ms": 300}


@pytest.mark.asyncio
async def test_service_omits_parameters_key_when_none() -> None:
    driver = FakeMqttDriver()
    service = ActuationService(mqtt_driver=driver)
    command = ActuationCommand(device_id="esp32-f", action=ActuationAction.FAN_OFF)

    await service.publish_with_device_ack(command)

    _, payload = driver.published_calls[0]
    assert "parameters" not in payload


@pytest.mark.asyncio
async def test_service_returns_true_when_driver_acks() -> None:
    driver = FakeMqttDriver(ack_result=True)
    service = ActuationService(mqtt_driver=driver)
    command = ActuationCommand(device_id="esp32-g", action=ActuationAction.PUMP_OFF)

    result = await service.publish_with_device_ack(command)

    assert result is True


@pytest.mark.asyncio
async def test_service_returns_false_when_driver_times_out() -> None:
    driver = FakeMqttDriver(ack_result=False)
    service = ActuationService(mqtt_driver=driver)
    command = ActuationCommand(device_id="esp32-h", action=ActuationAction.PUMP_OFF)

    result = await service.publish_with_device_ack(command)

    assert result is False


def test_service_resolve_ack_delegates_to_driver() -> None:
    driver = FakeMqttDriver(ack_result=True)
    service = ActuationService(mqtt_driver=driver)

    result = service.resolve_ack("some-command-id")

    assert result is True
    assert driver.resolve_calls == ["some-command-id"]


def test_service_resolve_ack_returns_false_when_not_pending() -> None:
    driver = FakeMqttDriver(ack_result=False)
    service = ActuationService(mqtt_driver=driver)

    result = service.resolve_ack("unknown-id")

    assert result is False


# ── handle_ack_message ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ack_listener_returns_false_when_command_id_missing() -> None:
    fake_service = FakeActuationService()
    result = await handle_ack_message(
        topic="commands/greenhouse/esp32-a/ack",
        payload={},
        service=fake_service,  # type: ignore[arg-type]
    )
    assert result is False
    assert fake_service.resolve_calls == []


@pytest.mark.asyncio
async def test_ack_listener_calls_resolve_with_command_id() -> None:
    fake_service = FakeActuationService(resolve_result=True)
    cid = str(uuid4())

    result = await handle_ack_message(
        topic="commands/greenhouse/esp32-a/ack",
        payload={"command_id": cid},
        service=fake_service,  # type: ignore[arg-type]
    )

    assert result is True
    assert fake_service.resolve_calls == [cid]


@pytest.mark.asyncio
async def test_ack_listener_returns_false_when_no_pending_command() -> None:
    fake_service = FakeActuationService(resolve_result=False)

    result = await handle_ack_message(
        topic="commands/greenhouse/esp32-a/ack",
        payload={"command_id": "stale-id"},
        service=fake_service,  # type: ignore[arg-type]
    )

    assert result is False


# ── RuleTriggeredHandler ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handler_publishes_command_for_valid_action() -> None:
    fake_service = FakeActuationService()
    handler = RuleTriggeredHandler(actuation_service=fake_service)  # type: ignore[arg-type]

    event = RuleTriggered(
        rule_id=uuid4(),
        device_id="esp32-auto",
        action="PUMP_ON",
        pulse_duration_ms=0,
    )

    await handler(event)

    assert len(fake_service.publish_calls) == 1
    cmd = fake_service.publish_calls[0]
    assert cmd.device_id == "esp32-auto"
    assert cmd.action == ActuationAction.PUMP_ON


@pytest.mark.asyncio
async def test_handler_drops_event_with_unknown_action(caplog) -> None:
    import logging

    fake_service = FakeActuationService()
    handler = RuleTriggeredHandler(actuation_service=fake_service)  # type: ignore[arg-type]

    event = RuleTriggered(
        rule_id=uuid4(),
        device_id="esp32-auto",
        action="INVALID_ACTION",
        pulse_duration_ms=0,
    )

    await handler(event)

    assert fake_service.publish_calls == []


@pytest.mark.asyncio
async def test_handler_includes_pulse_duration_in_parameters_when_nonzero() -> None:
    fake_service = FakeActuationService()
    handler = RuleTriggeredHandler(actuation_service=fake_service)  # type: ignore[arg-type]

    event = RuleTriggered(
        rule_id=uuid4(),
        device_id="esp32-auto",
        action="PUMP_ON",
        pulse_duration_ms=750,
    )

    await handler(event)

    cmd = fake_service.publish_calls[0]
    assert cmd.parameters == {"pulse_duration_ms": 750}


@pytest.mark.asyncio
async def test_handler_omits_parameters_when_pulse_duration_is_zero() -> None:
    fake_service = FakeActuationService()
    handler = RuleTriggeredHandler(actuation_service=fake_service)  # type: ignore[arg-type]

    event = RuleTriggered(
        rule_id=uuid4(),
        device_id="esp32-auto",
        action="FAN_OFF",
        pulse_duration_ms=0,
    )

    await handler(event)

    cmd = fake_service.publish_calls[0]
    assert cmd.parameters is None
