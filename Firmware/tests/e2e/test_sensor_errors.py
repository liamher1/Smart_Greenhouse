"""HIL test: firmware handles DHT22 sensor errors gracefully (verified via serial log).

Uses a modified diagram where the DHT22 reports 200°C — outside the valid range
[-40, 80] — so dht_sensor.read() raises ValueError on every call. The test confirms:
  1. The error is caught and logged to serial (not an unhandled exception / crash).
  2. The main loop keeps running (subsequent error lines appear, firmware is alive).
"""

from __future__ import annotations

import asyncio

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]

# Time budget: boot + 3 MQTT retries (~20s) + first sensor cycle (5s) + margin
SENSOR_WAIT_S = 45.0


async def test_sensor_error_is_caught_and_loop_continues(wokwi_error_process):
    """Firmware must log DHT read errors and keep running without crashing."""
    proc, serial_log = wokwi_error_process

    loop = asyncio.get_running_loop()
    deadline = loop.time() + SENSOR_WAIT_S
    error_count = 0

    while loop.time() < deadline:
        if serial_log.exists():
            content = serial_log.read_text(errors="replace")
            error_count = content.count("DHT read error (invalid value)")
            if error_count >= 2:
                break
        await asyncio.sleep(0.5)

    assert error_count >= 1, (
        "Expected 'DHT read error (invalid value)' in serial log — "
        "firmware may have crashed instead of recovering.\n"
        + (serial_log.read_text(errors="replace") if serial_log.exists() else "<log not created>")
    )
    assert error_count >= 2, (
        f"Only {error_count} error line(s) found — firmware may have stopped after the first error "
        "instead of continuing the loop"
    )
