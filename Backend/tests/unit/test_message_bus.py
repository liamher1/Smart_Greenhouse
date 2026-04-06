import unittest
from unittest.mock import patch

from Backend.src.base.infrastructure.message_bus import MessageBus


class TestMessageBus(unittest.IsolatedAsyncioTestCase):
    async def test_event_fanout_continues_and_logs_handler_errors(self):
        bus = MessageBus()

        class SensorEvent:
            def __init__(self, device_id):
                self.device_id = device_id

        handled = []

        async def ok_handler(event):
            handled.append(("ok", event.device_id))

        async def failing_handler(event):
            handled.append(("fail", event.device_id))
            raise RuntimeError("boom")

        bus.subscribe(SensorEvent, ok_handler)
        bus.subscribe(SensorEvent, failing_handler)

        with patch("Backend.src.base.infrastructure.message_bus.logger") as mock_logger:
            await bus.handle(SensorEvent("esp32-1"))

            self.assertEqual(len(handled), 2)
            self.assertTrue(mock_logger.opt.called)
            self.assertTrue(mock_logger.opt.return_value.error.called)

    async def test_command_failure_is_re_raised(self):
        bus = MessageBus()

        class RebootCommand:
            pass

        async def failing_command_handler(_command):
            raise ValueError("cannot reboot")

        bus.register_command(RebootCommand, failing_command_handler)

        with self.assertRaises(ValueError):
            await bus.handle(RebootCommand())


if __name__ == "__main__":
    unittest.main()

