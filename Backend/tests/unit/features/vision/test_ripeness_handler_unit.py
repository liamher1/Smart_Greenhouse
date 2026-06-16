from __future__ import annotations

from datetime import datetime, timezone

import pytest

from features.automation.handlers import RipenessHandler
from features.automation.models import PlantStage
from features.vision.events import FruitRipenessDetected


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> "FakeTransaction":
        self._session.begin_enter_calls += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self._session.begin_exit_calls += 1
        return False


class FakeSession:
    def __init__(self) -> None:
        self.enter_calls = 0
        self.exit_calls = 0
        self.begin_enter_calls = 0
        self.begin_exit_calls = 0

    async def __aenter__(self) -> "FakeSession":
        self.enter_calls += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self.exit_calls += 1
        return False

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)


class FakeRepository:
    def __init__(self, session: FakeSession, should_fail: bool = False) -> None:
        self.session = session
        self.should_fail = should_fail
        self.upserted: list[tuple[str, PlantStage]] = []

    async def upsert_greenhouse_state(self, device_id: str, stage: PlantStage) -> None:
        if self.should_fail:
            raise RuntimeError("simulated repository failure")
        self.upserted.append((device_id, stage))


class FakeBus:
    pass


def _make_event(stage: PlantStage = PlantStage.RED) -> FruitRipenessDetected:
    return FruitRipenessDetected(
        device_id="rpi-gh-01",
        timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
        stage=stage,
        green_pct=10.0,
        white_pink_pct=5.0,
        red_pct=85.0,
        confidence=0.92,
    )


@pytest.mark.asyncio
async def test_handler_opens_session_and_upserts_state() -> None:
    session = FakeSession()
    repo = FakeRepository(session)

    handler = RipenessHandler(
        session_factory=lambda: session,
        bus=FakeBus(),
        repository_factory=lambda s: repo,
    )

    await handler(_make_event(PlantStage.RED))

    assert session.enter_calls == 1
    assert session.begin_enter_calls == 1
    assert session.begin_exit_calls == 1
    assert session.exit_calls == 1
    assert repo.upserted == [("rpi-gh-01", PlantStage.RED)]


@pytest.mark.asyncio
async def test_handler_passes_correct_device_id_and_stage() -> None:
    session = FakeSession()
    repo = FakeRepository(session)

    handler = RipenessHandler(
        session_factory=lambda: session,
        bus=FakeBus(),
        repository_factory=lambda s: repo,
    )

    for stage in (PlantStage.GREEN, PlantStage.WHITE_PINK, PlantStage.RED):
        repo.upserted.clear()
        event = FruitRipenessDetected(
            device_id="rpi-gh-02",
            timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            stage=stage,
            green_pct=33.0,
            white_pink_pct=34.0,
            red_pct=33.0,
            confidence=0.5,
        )
        await handler(event)
        assert repo.upserted == [("rpi-gh-02", stage)]


@pytest.mark.asyncio
async def test_handler_propagates_repository_error() -> None:
    session = FakeSession()
    repo = FakeRepository(session, should_fail=True)

    handler = RipenessHandler(
        session_factory=lambda: session,
        bus=FakeBus(),
        repository_factory=lambda s: repo,
    )

    with pytest.raises(RuntimeError, match="simulated repository failure"):
        await handler(_make_event())
