from datetime import datetime, timezone
import unittest

from Backend.src.features.telemetry.events import TelemetryRecorded
from Backend.src.features.telemetry.handlers import TelemetryEventHandler


class FakeTransaction:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        self._session._in_transaction = True
        return self

    async def __aexit__(self, exc_type, _exc, _tb):
        # Keep in_transaction=True when failing so handler's defensive rollback path is testable.
        if exc_type is None:
            self._session._in_transaction = False
        return False


class FakeSession:
    def __init__(self):
        self.entered = False
        self.closed = False
        self.rollback_calls = 0
        self._in_transaction = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        self.closed = True

    def begin(self):
        return FakeTransaction(self)

    def in_transaction(self):
        return self._in_transaction

    async def rollback(self):
        self.rollback_calls += 1
        self._in_transaction = False


class FakeRepository:
    def __init__(self, session, should_fail=False):
        self.session = session
        self.should_fail = should_fail
        self.readings = []

    async def add_telemetry_reading(self, telemetry_reading):
        if self.should_fail:
            raise RuntimeError("db insert failed")
        self.readings.append(telemetry_reading)


class TestTelemetryHandlerSessionPolicy(unittest.IsolatedAsyncioTestCase):
    async def test_creates_new_session_per_event_and_closes_sessions(self):
        sessions = []
        repositories = []

        def session_factory():
            session = FakeSession()
            sessions.append(session)
            return session

        def repository_factory(session):
            repo = FakeRepository(session)
            repositories.append(repo)
            return repo

        handler = TelemetryEventHandler(session_factory=session_factory, repository_factory=repository_factory)

        event_1 = TelemetryRecorded(
            temperature=21.0,
            humidity=55.0,
            device_id="esp32-1",
            timestamp=datetime.now(timezone.utc),
        )
        event_2 = TelemetryRecorded(
            temperature=22.0,
            humidity=56.0,
            device_id="esp32-2",
            timestamp=datetime.now(timezone.utc),
        )

        await handler(event_1)
        await handler(event_2)

        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(session.closed for session in sessions))
        self.assertTrue(all(session.rollback_calls == 0 for session in sessions))
        self.assertEqual(sum(len(repo.readings) for repo in repositories), 2)

    async def test_rolls_back_and_re_raises_on_repository_error(self):
        sessions = []

        def session_factory():
            session = FakeSession()
            sessions.append(session)
            return session

        def repository_factory(session):
            return FakeRepository(session, should_fail=True)

        handler = TelemetryEventHandler(session_factory=session_factory, repository_factory=repository_factory)
        event = TelemetryRecorded(
            temperature=21.0,
            humidity=55.0,
            device_id="esp32-1",
            timestamp=datetime.now(timezone.utc),
        )

        with self.assertRaises(RuntimeError):
            await handler(event)

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].rollback_calls, 1)
        self.assertTrue(sessions[0].closed)


if __name__ == "__main__":
    unittest.main()

