# System Architecture

## Overview

Smart Strawberry Greenhouse — end-to-end data flow across all components.

```
┌──────────────────────────── PHYSICAL LAYER ────────────────────────────────┐
│                                                                             │
│   Soil Moisture (ADC) ──┐                                                   │
│   DHT22 (Temp/Hum)  ────┼──► ESP32-S2 (MicroPython Firmware)               │
│   Float Switch      ────┘         │  every 30 min  │  every 100 ms          │
│                                   │  publish       │  check_msg()           │
│                                   │  telemetry     │  + safety interlock    │
│                                   │                │                        │
│                     Water Pump ◄──┼── relay cmd    │                        │
│                     Fan        ◄──┘                │                        │
└───────────────────────────────────┼────────────────────────────────────────┘
                                    │ MQTT: greenhouse/telemetry/esp32-gh-01
┌───────────────────────────────────┼────────────────────────────────────────┐
│              RASPBERRY PI (Mosquitto Broker + Vision Agent)                 │
│                                   │                                         │
│   Mosquitto ◄─────────────────────┘    also publishes every 4 hours:       │
│       │                                greenhouse/vision/rpi-gh-01          │
│       │                                        ▲                            │
│       │    Pi Camera Module 3                  │                            │
│       │    ──────────────────                  │                            │
│       │    autofocus → capture ──► YOLOv8 (Strawberry Detect)              │
│       │                            Flower / Green Strawberry → green_pct   │
│       │                            Red Strawberry            → red_pct     │
│       │                            dominant stage → PlantStage             │
└───────┼────────────────────────────────────────────────────────────────────┘
        │ MQTT subscriptions
┌───────┼────────────────────────────────────────────────────────────────────┐
│       │               FASTAPI BACKEND                                       │
│       ▼                                                                     │
│   MqttDriver (aiomqtt)                                                      │
│       │                                                                     │
│   ┌───┴──────────────────┬──────────────────────┬────────────────────┐     │
│   │ greenhouse/           │ greenhouse/           │ commands/          │     │
│   │ telemetry/+           │ vision/+              │ greenhouse/+/ack   │     │
│   ▼                       ▼                       ▼                   │     │
│ TelemetryEntrypoint   VisionEntrypoint     ActuationAckListener       │     │
│   │                       │                       │                   │     │
│   ▼                       ▼                       ▼                   │     │
│ TelemetryRecorded   FruitRipenessDetected  resolve_ack(command_id)    │     │
│ {temp, hum,         {stage, green_pct,                                │     │
│  soil_moisture,      white_pink_pct,                                  │     │
│  water_level}        red_pct, confidence}                             │     │
│   │                       │                                           │     │
│   └───────────┬───────────┘                                           │     │
│               ▼                                                       │     │
│          MessageBus (fan-out)                                         │     │
│               │                                                       │     │
│   ┌───────────┼───────────────────┬───────────────────────┐          │     │
│   ▼           ▼                   ▼                       ▼          │     │
│ Telemetry  Telemetry-         Ripeness-              RuleTriggered-  │     │
│ EventHndlr AutomationHndlr    Handler                Handler         │     │
│   │           │                   │                       │          │     │
│   ▼           │                   ▼                       ▼          │     │
│ persist    1. get stage        upsert              ActuationService   │     │
│ to DB      2. query rules      GreenhouseState     publish_with_ack() │     │
│            3. evaluate         in DB               │                  │     │
│            4. if triggered ──► RuleTriggered       │                  │     │
│                                event               │                  │     │
│                                                    ▼                  │     │
│                                         MQTT publish                  │     │
│                                   commands/greenhouse/esp32-gh-01     │     │
│                                   {command_id, action: "PUMP_ON",    │     │
│                                    parameters: {pulse_ms: 3000}}     │     │
│                                                    │                  │     │
│                                    waits for ACK ◄─┘ (5 s timeout)   │     │
│                                                                       │     │
│   ┌──────────────────── PostgreSQL ────────────────────────────────┐ │     │
│   │  telemetryreading   │  greenhousestate  │  controlrule         │ │     │
│   │  wateringpolicy     │  wateringtimes                           │ │     │
│   └─────────────────────────────────────────────────────────────── ┘ │     │
│                                                                       │     │
│   REST API (FastAPI)                                                  │     │
│   POST /api/v1/actuation/{device_id}/command   (manual override)     │     │
│   GET|POST|PATCH|DELETE /api/v1/automation/rules                     │     │
│   GET|POST /api/v1/automation/policies                               │     │
│   GET /api/v1/automation/state                                       │     │
└───────────────────────────────────────────────────────────────────────┘
        │ commands/greenhouse/esp32-gh-01
┌───────▼────────────────────────────────────────────────────────────────┐
│                  ESP32-S2 RECEIVES COMMAND                              │
│                                                                         │
│   _on_command()                                                         │
│       │                                                                 │
│   Safety interlock: float_switch.is_empty()?                           │
│       YES → block PUMP_ON, log warning                                  │
│       NO  → pump.on()  /  fan.on()  /  pump.off()  /  fan.off()       │
│                                                                         │
│   ACK → commands/greenhouse/esp32-gh-01/ack  {command_id: "..."}       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Brix Feedback Loop (Autonomous Ripening)

```
Pi Camera detects Red Strawberry > 60 %
          │
          ▼
  FruitRipenessDetected { stage: "Red", red_pct: 74, ... }
          │
          ▼
  RipenessHandler → GreenhouseState.plant_stage = "Red"  (DB)
          │
          ▼  (next telemetry, 30 min later)
  TelemetryAutomationHandler
    queries ControlRule WHERE plant_stage = 'Red' OR NULL
    evaluates: soil_moisture (16.0) < threshold (20.0) → True
          │
          ▼
  RuleTriggered { action: "PUMP_ON", pulse_duration_ms: 3000 }
          │
          ▼
  PUMP_ON sent to ESP32 (short pulse = water stress maintained)
          │
          ▼
  Albion strawberry achieves 11–13° Brix at harvest
```

No code changes required — thresholds live in the `ControlRule` table.

---

## Slice Summary

| Slice | Location | Responsibility |
|---|---|---|
| Firmware | `Firmware/` | Sensors → MQTT telemetry; receive + execute commands; safety interlock |
| Telemetry | `Backend/src/features/telemetry/` | Ingest MQTT telemetry → persist to DB |
| Actuation | `Backend/src/features/actuation/` | Publish MQTT commands → wait for device ACK |
| Automation | `Backend/src/features/automation/` | Rules engine: evaluate telemetry against DB thresholds; fire RuleTriggered |
| Vision | `Backend/src/features/vision/` | Ingest Pi inference results → FruitRipenessDetected event |
| RaspberryPi | `RaspberryPi/` | Capture image → YOLOv8 inference → publish vision MQTT message |

---

## MQTT Topic Map

| Topic | Direction | Published by | Consumed by |
|---|---|---|---|
| `greenhouse/telemetry/<device_id>` | ESP32 → Broker → Backend | ESP32 firmware | TelemetryEntrypoint |
| `greenhouse/vision/<device_id>` | Pi → Broker → Backend | Pi vision agent | VisionEntrypoint |
| `commands/greenhouse/<device_id>` | Backend → Broker → ESP32 | ActuationService | ESP32 firmware |
| `commands/greenhouse/<device_id>/ack` | ESP32 → Broker → Backend | ESP32 firmware | ActuationAckListener |

---

## Startup Wiring (main.py)

```
init_db()                         → creates all tables
MessageBus()                      → instantiated
TelemetryEventHandler             → subscribed to TelemetryRecorded
TelemetryAutomationHandler        → subscribed to TelemetryRecorded
RipenessHandler                   → subscribed to FruitRipenessDetected
RuleTriggeredHandler              → subscribed to RuleTriggered
MqttDriver.connect()              → connects to broker
register_telemetry_entrypoint()   → routes greenhouse/telemetry/+
register_vision_entrypoint()      → routes greenhouse/vision/+
register_actuation_ack_listener() → routes commands/greenhouse/+/ack
mqtt_driver.run()                 → async listener loop (background task)
FastAPI serves HTTP               → actuation + automation REST endpoints
```

---

## Message Envelope (all MQTT messages)

All MQTT messages share the same `IncomingMqttDto` wrapper:

```json
{
  "header": {
    "type": "telemetry",
    "device_id": "esp32-gh-01",
    "timestamp": "2026-06-02T10:00:00+00:00"
  },
  "payload": { ... }
}
```

`type` values: `"telemetry"` | `"vision"`
