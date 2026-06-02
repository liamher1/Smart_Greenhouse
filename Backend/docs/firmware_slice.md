# Firmware Slice (ESP32-S2 MicroPython)

## Purpose

The ESP32-S2 is the physical edge node. It reads environmental sensors every 30 minutes and publishes telemetry to the MQTT broker. In parallel it continuously polls for incoming actuation commands (pump, fan) and enforces a local hardware safety interlock that overrides any MQTT command if the water tank is empty.

## Files

| File | Role |
|---|---|
| `Firmware/config.py` | GPIO pin assignments, MQTT settings, device ID, timing |
| `Firmware/boot.py` | Wi-Fi connection on device boot (10 s timeout) |
| `Firmware/main.py` | Main loop: telemetry cadence, MQTT command handler, reconnect |
| `Firmware/soil_sensor.py` | ADC read on `SOIL_MOISTURE_PIN` (ATTN_11DB, 0–4095 raw) |
| `Firmware/dht_sensor.py` | DHT22 read with sanity bounds check |
| `Firmware/float_switch.py` | Digital input `FLOAT_SWITCH_PIN` with pull-up; HIGH = tank empty |
| `Firmware/pump.py` | Water pump relay driver with active-high/low polarity config |
| `Firmware/fan.py` | Ventilation fan relay driver with active-high/low polarity config |
| `Firmware/mqtt_client.py` | Wraps `umqtt.robust`; connect, subscribe, publish, check_msg |
| `Firmware/ntp_sync.py` | Syncs RTC from NTP on boot for accurate timestamps |

## GPIO Pin Assignments (`config.py`)

| Pin | Signal | Direction | Notes |
|---|---|---|---|
| `GPIO 10` | Soil moisture (ADC) | IN | ATTN_11DB; 0 = wet, 4095 = dry |
| `GPIO 4` | DHT22 data | IN | One-wire protocol |
| `GPIO 7` | Float switch | IN | PULL_UP; HIGH = tank empty |
| `GPIO 5` | Pump relay | OUT | Active-HIGH; LOW on boot |
| `GPIO 6` | Fan relay | OUT | Active-HIGH; LOW on boot |

## Main Loop Architecture

```
boot.py: connect WiFi (10 s timeout)
         NTP sync

main.py:
    ┌─────────────────────── while True ───────────────────────────────┐
    │                                                                   │
    │  1. Safety interlock (every iteration, ~100 ms)                   │
    │     if float_switch.is_empty():                                   │
    │         pump.off()    ← overrides ANY MQTT PUMP_ON               │
    │                                                                   │
    │  2. MQTT check_msg() (non-blocking)                               │
    │     → _on_command(topic, data)                                    │
    │       PUMP_ON  → safety check → pump.on()                        │
    │       PUMP_OFF → pump.off()                                       │
    │       FAN_ON   → fan.on()                                         │
    │       FAN_OFF  → fan.off()                                        │
    │       → ACK published on commands/greenhouse/<id>/ack             │
    │                                                                   │
    │  3. Telemetry cadence (non-blocking delta time)                   │
    │     if ticks_diff(now, last_publish) >= 1800 s:                   │
    │         read DHT22   → (temperature, humidity)                    │
    │         read ADC     → soil_moisture (raw 0–4095)                 │
    │         read float   → water_level (0 or 1)                       │
    │         publish JSON to greenhouse/telemetry/<device_id>          │
    │         last_publish = now                                        │
    │                                                                   │
    │  4. time.sleep_ms(100)                                            │
    └───────────────────────────────────────────────────────────────────┘
```

## Telemetry Payload

Published to `greenhouse/telemetry/<DEVICE_ID>` every 30 minutes:

```json
{
  "header": {
    "type": "telemetry",
    "device_id": "esp32-gh-01",
    "timestamp": "2026-06-02T10:00:00+00:00"
  },
  "payload": {
    "temperature": 22.5,
    "humidity": 65.0,
    "soil_moisture": 2048,
    "water_level": 0
  }
}
```

> `soil_moisture` is the raw ADC value (0–4095). The backend stores it as-is; calibration to % is handled at the rule threshold level.

## Command & ACK

**Received on** `commands/greenhouse/<DEVICE_ID>`:

```json
{
  "command_id": "8c3b77f4-...",
  "action": "PUMP_ON",
  "parameters": { "pulse_duration_ms": 3000 }
}
```

**ACK sent on** `commands/greenhouse/<DEVICE_ID>/ack`:

```json
{ "command_id": "8c3b77f4-..." }
```

## Safety Interlock

The float switch safety check runs **every loop iteration** (every 100 ms), not only when a command arrives. This means even if PUMP_ON is executed and the tank drains while the pump is running, the next loop tick forces the pump off before the backend issues another command.

```
MQTT PUMP_ON received
    │
    ├─ float_switch.is_empty() == True  →  blocked, ACK NOT sent
    │
    └─ float_switch.is_empty() == False →  pump.on(), ACK sent
                                               │
                             100 ms later: float_switch.is_empty()?
                                           True → pump.off() (interlock)
```

## Connection Resilience

- **Boot:** `_connect_mqtt()` retries up to 3 times with 5 s delay; falls back to offline mode (telemetry printed locally, no publish).
- **Runtime drop:** `_reconnect_with_backoff()` retries with exponential delay starting at 2 s, capped at 60 s.

## Development vs Production Config

`config.py` has dual-mode comments:

```python
WIFI_SSID              = "Wokwi-GUEST"      # simulation
MQTT_BROKER            = "host.wokwi.internal"   # simulation
TELEMETRY_INTERVAL_SEC = 5                   # fast feedback in Wokwi
# Production:
# WIFI_SSID = "YourSSID"
# MQTT_BROKER = "192.168.1.x"   (Pi LAN IP)
# TELEMETRY_INTERVAL_SEC = 1800
```
