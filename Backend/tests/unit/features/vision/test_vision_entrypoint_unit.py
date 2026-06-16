from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from features.automation.models import PlantStage
from features.vision.entrypoints import VisionEntrypoint
from features.vision.events import FruitRipenessDetected


class FakeBus:
    def __init__(self) -> None:
        self.handled: list = []

    async def handle(self, event) -> None:
        self.handled.append(event)


_VALID_ENVELOPE = {
    "header": {
        "type": "vision",
        "device_id": "rpi-gh-01",
        "timestamp": "2026-06-16T12:00:00+00:00",
    },
    "payload": {
        "stage": "Green",
        "green_pct": 80.0,
        "white_pink_pct": 10.0,
        "red_pct": 10.0,
        "confidence": 0.85,
    },
}


def _encode(data: dict) -> bytes:
    return json.dumps(data).encode()


@pytest.mark.asyncio
async def test_valid_message_dispatches_fruit_ripeness_event() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    await ep.on_vision_message("greenhouse/vision/rpi-gh-01", _encode(_VALID_ENVELOPE))

    assert len(bus.handled) == 1
    event = bus.handled[0]
    assert isinstance(event, FruitRipenessDetected)
    assert event.device_id == "rpi-gh-01"
    assert event.stage == PlantStage.GREEN
    assert event.green_pct == 80.0
    assert event.white_pink_pct == 10.0
    assert event.red_pct == 10.0
    assert event.confidence == 0.85


@pytest.mark.asyncio
async def test_device_id_and_timestamp_injected_from_header() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    envelope = {
        **_VALID_ENVELOPE,
        "header": {**_VALID_ENVELOPE["header"], "device_id": "rpi-gh-99", "timestamp": "2026-01-01T00:00:00+00:00"},
    }

    await ep.on_vision_message("greenhouse/vision/rpi-gh-99", _encode(envelope))

    event = bus.handled[0]
    assert event.device_id == "rpi-gh-99"
    assert event.timestamp == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_wrong_header_type_is_silently_ignored() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    envelope = {**_VALID_ENVELOPE, "header": {**_VALID_ENVELOPE["header"], "type": "telemetry"}}

    await ep.on_vision_message("greenhouse/vision/rpi-gh-01", _encode(envelope))

    assert bus.handled == []


@pytest.mark.asyncio
async def test_invalid_json_is_silently_ignored() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    await ep.on_vision_message("greenhouse/vision/rpi-gh-01", b"not-valid-json{{{")

    assert bus.handled == []


@pytest.mark.asyncio
async def test_missing_payload_fields_are_silently_ignored() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    envelope = {
        "header": _VALID_ENVELOPE["header"],
        "payload": {"stage": "Green"},  # missing pct + confidence
    }

    await ep.on_vision_message("greenhouse/vision/rpi-gh-01", _encode(envelope))

    assert bus.handled == []


@pytest.mark.asyncio
async def test_confidence_above_one_is_silently_ignored() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    envelope = {
        **_VALID_ENVELOPE,
        "payload": {**_VALID_ENVELOPE["payload"], "confidence": 1.5},
    }

    await ep.on_vision_message("greenhouse/vision/rpi-gh-01", _encode(envelope))

    assert bus.handled == []


@pytest.mark.asyncio
async def test_all_three_stages_are_accepted() -> None:
    bus = FakeBus()
    ep = VisionEntrypoint(bus)

    for stage_str, expected in [
        ("Green", PlantStage.GREEN),
        ("WhitePink", PlantStage.WHITE_PINK),
        ("Red", PlantStage.RED),
    ]:
        bus.handled.clear()
        envelope = {**_VALID_ENVELOPE, "payload": {**_VALID_ENVELOPE["payload"], "stage": stage_str}}
        await ep.on_vision_message("greenhouse/vision/rpi-gh-01", _encode(envelope))
        assert bus.handled[0].stage == expected
