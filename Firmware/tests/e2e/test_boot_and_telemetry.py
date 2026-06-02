"""HIL test: firmware boots and produces valid telemetry (verified via serial log).

Boot path verified: WiFi connect → NTP sync → MQTT retries → offline mode → sensor loop.
Telemetry JSON is printed to serial on every cycle and parsed here for schema validation.
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]

# Time budget: WiFi(~3s) + NTP(~2s) + 3 MQTT retries(~15s) + first telemetry(5s) = ~25s
BOOT_TIMEOUT_S = 50.0


async def _wait_for_pattern(serial_log, pattern: str, timeout_s: float) -> re.Match | None:
    """Poll the serial log file until a line matching pattern is found."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        if serial_log.exists():
            content = serial_log.read_text(errors="replace")
            m = re.search(pattern, content)
            if m:
                return m
        await asyncio.sleep(0.5)
    return None


async def test_firmware_boots_and_connects_wifi(wokwi_process):
    """Serial log must show a successful WiFi connection."""
    _, serial_log = wokwi_process
    m = await _wait_for_pattern(serial_log, r"WiFi connected: (\S+)", 30.0)
    assert m, "Firmware did not print 'WiFi connected' within 30s"
    ip = m.group(1)
    assert ip.startswith("10."), f"Expected Wokwi-GUEST IP (10.x.x.x), got {ip}"


async def test_firmware_syncs_ntp(wokwi_process):
    """Serial log must show a successful NTP sync with a plausible timestamp."""
    _, serial_log = wokwi_process
    m = await _wait_for_pattern(serial_log, r"NTP synced: (\d{4}-\d{2}-\d{2})", 30.0)
    assert m, "Firmware did not print 'NTP synced' within 30s"
    year = int(m.group(1)[:4])
    assert year >= 2024, f"NTP year {year} is implausibly old"


async def test_firmware_publishes_telemetry_with_valid_schema(wokwi_process):
    """Firmware must print a JSON telemetry line with the correct schema."""
    _, serial_log = wokwi_process
    m = await _wait_for_pattern(serial_log, r'Telemetry: (\{.+\})', BOOT_TIMEOUT_S)
    assert m, (
        f"No 'Telemetry: {{...}}' line in serial log within {BOOT_TIMEOUT_S}s — "
        "firmware may have crashed before reaching the sensor loop"
    )

    payload = json.loads(m.group(1))

    header = payload["header"]
    assert header["type"] == "telemetry"
    assert header["device_id"] == "esp32-gh-01"
    assert header["timestamp"], "timestamp must be non-empty"

    data = payload["payload"]
    temp = data["temperature"]
    hum  = data["humidity"]
    assert -40.0 <= temp <= 80.0, f"temperature {temp}°C is out of DHT22 range"
    assert 0.0   <= hum  <= 100.0, f"humidity {hum}% is out of range"

    soil = data["soil_moisture"]
    assert isinstance(soil, int) and 0 <= soil <= 4095, f"soil_moisture {soil} out of ADC range"

    water = data["water_level"]
    assert water in (0, 1), f"water_level must be 0 or 1, got {water}"
