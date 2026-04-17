from __future__ import annotations

from datetime import datetime, timezone

import pytest

from features.telemetry.events import TelemetryRecorded
from features.telemetry.handlers import TelemetryEventHandler


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> "FakeTransaction":
        self._session.begin_enter_calls += 1
        self._session._in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self._session.begin_exit_calls += 1
        # On success, transaction is considered closed.
        # On failure we intentionally keep it active so handler-level rollback can run.
        if exc_type is None:
            self._session._in_transaction = False
        return False


class FakeSession:
    def __init__(self) -> None:
        self.enter_calls = 0
        self.exit_calls = 0
        self.begin_enter_calls = 0
        self.begin_exit_calls = 0
        self.rollback_calls = 0
        self.closed = False
        self._in_transaction = False

    async def __aenter__(self) -> "FakeSession":
        self.enter_calls += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self.exit_calls += 1
        self.closed = True
        return False

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    def in_transaction(self) -> bool:
        return self._in_transaction

    async def rollback(self) -> None:
        self.rollback_calls += 1
        self._in_transaction = False


class FakeRepository:
    def __init__(self, session: FakeSession, should_fail: bool = False) -> None:
        self.session = session
        self.should_fail = should_fail
        self.saved = []

    async def add_telemetry_reading(self, telemetry_reading) -> None:
        if self.should_fail:
            raise RuntimeError("simulated repository failure")
        self.saved.append(telemetry_reading)


@pytest.mark.asyncio
async def test_handler_opens_transaction_saves_and_closes_session() -> None:
    """Verify the handler opens a session, saves the reading, and closes cleanly."""
    session = FakeSession()
    repository = FakeRepository(session)

    def session_factory() -> FakeSession:
        return session

    def repository_factory(current_session: FakeSession) -> FakeRepository:
        assert current_session is session
        return repository

    handler = TelemetryEventHandler(
        session_factory=session_factory,
        repository_factory=repository_factory,
    )

    event = TelemetryRecorded(
        temperature=25.5,
        humidity=61.2,
        device_id="esp32-greenhouse-a",
        timestamp=datetime(2026, 4, 7, 12, 30, tzinfo=timezone.utc),
    )

    await handler(event)

    assert session.enter_calls == 1
    assert session.begin_enter_calls == 1
    assert session.begin_exit_calls == 1
    assert session.exit_calls == 1
    assert session.rollback_calls == 0
    assert session.closed is True

    assert len(repository.saved) == 1
    saved = repository.saved[0]
    assert saved.temperature == 25.5
    assert saved.humidity == 61.2
    assert saved.device_id == "esp32-greenhouse-a"
    assert saved.timestamp == event.timestamp


@pytest.mark.asyncio
async def test_handler_rolls_back_and_reraises_when_repository_fails() -> None:
    """Verify repository failures trigger rollback and are re-raised to the caller."""
    session = FakeSession()
    repository = FakeRepository(session, should_fail=True)

    def session_factory() -> FakeSession:
        return session

    def repository_factory(current_session: FakeSession) -> FakeRepository:
        assert current_session is session
        return repository

    handler = TelemetryEventHandler(
        session_factory=session_factory,
        repository_factory=repository_factory,
    )

    event = TelemetryRecorded(
        temperature=24.0,
        humidity=58.0,
        device_id="esp32-greenhouse-b",
        timestamp=datetime(2026, 4, 7, 12, 31, tzinfo=timezone.utc),
    )

    with pytest.raises(RuntimeError, match="simulated repository failure"):
        await handler(event)

    assert session.enter_calls == 1
    assert session.begin_enter_calls == 1
    assert session.begin_exit_calls == 1
    assert session.exit_calls == 1
    assert session.rollback_calls == 1
    assert session.closed is True
