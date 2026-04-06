from datetime import datetime, timezone
import unittest

from pydantic import ValidationError

from Backend.src.features.telemetry.events import TelemetryRecorded


class TestTelemetryRecordedValidation(unittest.TestCase):
    def test_accepts_valid_event(self):
        event = TelemetryRecorded(
            temperature=24.2,
            humidity=58.0,
            device_id="esp32-01",
            timestamp=datetime.now(timezone.utc),
        )

        self.assertEqual(event.device_id, "esp32-01")

    def test_rejects_humidity_out_of_range(self):
        with self.assertRaises(ValidationError):
            TelemetryRecorded(
                temperature=20.0,
                humidity=150.0,
                device_id="esp32-01",
                timestamp=datetime.now(timezone.utc),
            )

    def test_rejects_temperature_out_of_range(self):
        with self.assertRaises(ValidationError):
            TelemetryRecorded(
                temperature=-60.0,
                humidity=30.0,
                device_id="esp32-01",
                timestamp=datetime.now(timezone.utc),
            )

    def test_rejects_empty_device_id(self):
        with self.assertRaises(ValidationError):
            TelemetryRecorded(
                temperature=21.0,
                humidity=33.0,
                device_id="   ",
                timestamp=datetime.now(timezone.utc),
            )


if __name__ == "__main__":
    unittest.main()

