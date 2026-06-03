# ESP32-S2 Hardware Wiring Guide

A complete, beginner-friendly checklist for wiring the Smart Greenhouse from scratch to a running system. No prior electronics experience required — read each section fully before touching any wires, and follow the steps in order.

**Golden rules:**
- Never plug anything into power until this guide tells you to
- If something smells hot or you see a spark — unplug immediately
- When in doubt, re-read the step. There is no rush.

---

## Section 1 — Shopping List

### The Brain
| Item | Notes |
|---|---|
| **ESP32-S2 development board** | Any standard board — "Lolin S2 Mini" or "ESP32-S2 DevKit" are common |
| **Micro-USB or USB-C cable** | Matches your board's port — used for both power and programming |

### Sensors
| Item | Notes |
|---|---|
| **DHT22 sensor module** | Buy the **3-pin module version** (has a small PCB attached), not the bare 4-pin chip. The module has the required resistor already built in |
| **Capacitive soil moisture sensor** | The long thin probe. Make sure it says "capacitive" — not "resistive" (resistive ones corrode quickly) |
| **Float switch** | A small cylinder with a wire coming out each end. Used to detect water level |

### Actuators
| Item | Notes |
|---|---|
| **5V single-channel relay module × 2** | One for the pump, one for the fan. Must say "5V relay module" |
| **Small 5V water pump** | A submersible aquarium-style mini pump works well |
| **Small 5V fan** | A 5V PC-style fan or greenhouse ventilation fan |

### Wiring & Power
| Item | Notes |
|---|---|
| **Breadboard** | Full-size (830 tie-points) recommended |
| **Jumper wires** | A variety pack — male-to-male are the most common type needed |
| **5V power supply** | A USB phone charger — at least 2A recommended |

---

## Section 2 — Key Concepts (2-Minute Read)

**GND (Ground)** — The "return path" for all electricity. Every single component must share a common GND with the ESP32. This is the most important connection in the whole system.

**3.3V** — The ESP32 runs on 3.3 volts. Its GPIO pins output 3.3V as a "HIGH" signal and 0V as "LOW." The sensors in this build run on 3.3V.

**5V (also called VUSB or VIN)** — The relay modules need 5V to operate. The ESP32 board has a pin labelled "5V," "VUSB," or "VIN" that passes through the USB cable voltage — use this to power the relay modules.

**GPIO Pin** — General Purpose Input/Output. These are the numbered pins on the ESP32 that the firmware talks to. "GPIO 4" means pin number 4.

**Relay Module** — An electrically controlled switch. The ESP32 (low power, 3.3V) flips the relay, and the relay switches a separate higher-power circuit (for the pump or fan). The two circuits are physically isolated — the pump's electricity never touches the ESP32.

---

## Section 3 — Prepare Your Workspace

- [ ] Clear a flat, dry surface
- [ ] Place the breadboard in front of you
- [ ] Place the ESP32 board in the centre of the breadboard, straddling the centre gap, so each row of pins is accessible on either side
- [ ] Leave the USB cable **unplugged** for now

---

## Section 4 — Understanding Your Breadboard

A breadboard has two types of connections:

- **Power rails** — the two long horizontal rows along each edge, marked `+` (positive) and `−` (negative/GND). Everything in the same rail is connected.
- **Component rows** — the short vertical columns in the middle. Each set of 5 holes in a column is connected together.

---

## Section 5 — Establish Power Rails

**Step 5.1 — Connect 3.3V to the breadboard positive rail**
- [ ] Find the pin on your ESP32 labelled **3V3** (or 3.3V)
- [ ] Run a red jumper wire from that pin to the `+` rail at the top of the breadboard

**Step 5.2 — Connect 5V to the breadboard**
- [ ] Find the pin on your ESP32 labelled **5V**, **VUSB**, or **VIN**
- [ ] Run a jumper wire from that pin to a spare column in the middle of the breadboard — label it mentally as "5V rail"

**Step 5.3 — Connect GND to the breadboard negative rail**
- [ ] Find any pin on your ESP32 labelled **GND**
- [ ] Run a black jumper wire from that pin to the `−` rail at the top of the breadboard

**Step 5.4 — Bridge the rails (if your breadboard has two halves)**
Many breadboards have a gap in the middle of the power rails. If yours does:
- [ ] Run a short jumper connecting the top-half `+` rail to the bottom-half `+` rail
- [ ] Run a short jumper connecting the top-half `−` rail to the bottom-half `−` rail

> You now have a red `+` rail at 3.3V and a black `−` rail at GND running the full length of the breadboard. The 5V point is a marked column.

---

## Section 6 — DHT22 (Temperature & Humidity Sensor)

Measures air temperature and humidity. The 3-pin module has pins labelled `VCC`, `DATA`, and `GND`.

- [ ] Push the DHT22 module into the breadboard on the left side
- [ ] `VCC` → `+` rail (3.3V)
- [ ] `GND` → `−` rail (GND)
- [ ] `DATA` → **GPIO 4** on the ESP32

> The ESP32 can now read air temperature and humidity on GPIO 4.

---

## Section 7 — Capacitive Soil Moisture Sensor

The long probe you push into the soil. The 3-pin header at the top is labelled `VCC`, `GND`, and `AOUT` (Analog Output).

- [ ] Push the 3-pin header end of the sensor into the breadboard
- [ ] `VCC` → `+` rail (3.3V)
- [ ] `GND` → `−` rail (GND)
- [ ] `AOUT` → **GPIO 10** on the ESP32

> The firmware converts the raw ADC reading (0–4095) to a 0–100% moisture percentage using the calibration constants `SOIL_ADC_DRY = 3200` and `SOIL_ADC_WET = 1100` in `config.py`. If readings seem off, hold the probe in dry air then in water, note the raw values from the serial monitor, and update those constants.

---

## Section 8 — Float Switch (Water Level Detector)

Sits inside the water reservoir. When water is present the switch closes; when empty it opens. This is the **safety interlock** — the firmware checks it every 100 ms and will never run the pump dry.

The switch has 2 wires with no polarity — either wire can go to either connection.

- [ ] One wire → **GPIO 7** on the ESP32
- [ ] Other wire → `−` rail (GND)

> No resistor needed. The firmware enables the ESP32's internal pull-up resistor on GPIO 7 in software.

**How it works:**
- Water present → switch closes → GPIO 7 pulled to GND → reads LOW → `is_empty()` returns `False` → pump allowed
- Tank empty → switch opens → internal pull-up pulls GPIO 7 HIGH → reads HIGH → `is_empty()` returns `True` → pump blocked immediately

---

## Section 9 — Water Pump Relay Module

The relay module has 3 control pins on one side (`VCC`, `GND`, `IN`) and 3 screw terminals on the other (`COM`, `NO`, `NC`).

**Control side (connects to ESP32):**
- [ ] Place the relay module on the right side of the breadboard
- [ ] `VCC` → **5V column** (not the 3.3V rail)
- [ ] `GND` → `−` rail (GND)
- [ ] `IN` → **GPIO 5** on the ESP32

> Relay modules need 5V. Using 3.3V will cause the relay to click weakly or not at all.

**Switched side (connects to pump power):**

The pump needs its own 5V supply — do not take this from the ESP32's 5V pin (pumps draw too much current). Use a separate USB adapter with bare wires.

- [ ] Pump supply `+` → `COM` screw terminal
- [ ] Pump `+` wire → `NO` (Normally Open) screw terminal
- [ ] Pump `−` wire → pump supply `−` directly (this wire does NOT go through the relay)

> `NO` = Normally Open: the circuit is disconnected by default. When GPIO 5 goes HIGH the relay closes and the pump gets power.

---

## Section 10 — Ventilation Fan Relay Module

Identical to the pump relay wiring, using a second relay module and GPIO 6.

**Control side:**
- [ ] `VCC` → **5V column**
- [ ] `GND` → `−` rail (GND)
- [ ] `IN` → **GPIO 6** on the ESP32

**Switched side:**
- [ ] Fan supply `+` → `COM` screw terminal
- [ ] Fan `+` wire → `NO` screw terminal
- [ ] Fan `−` wire → fan supply `−` directly (not through the relay)

---

## Section 11 — Complete Wiring Reference

```
ESP32 Pin      Connects To
──────────────────────────────────────────────────────────
3V3        →   Breadboard + rail (3.3V power)
GND        →   Breadboard − rail (shared ground)
5V / VUSB  →   5V column (relay power)

GPIO 4     →   DHT22 DATA pin
GPIO 5     →   Pump relay IN pin
GPIO 6     →   Fan relay IN pin
GPIO 7     →   Float switch terminal A
GPIO 10    →   Soil sensor AOUT pin

DHT22 VCC      →   + rail (3.3V)
DHT22 GND      →   − rail (GND)

Soil VCC       →   + rail (3.3V)
Soil GND       →   − rail (GND)

Float switch B →   − rail (GND)

Pump relay VCC →   5V column
Pump relay GND →   − rail (GND)

Fan relay VCC  →   5V column
Fan relay GND  →   − rail (GND)

Pump supply +  →   Pump relay COM
Pump + wire    →   Pump relay NO
Pump − wire    →   Pump supply −   [direct, bypasses relay]

Fan supply +   →   Fan relay COM
Fan + wire     →   Fan relay NO
Fan − wire     →   Fan supply −    [direct, bypasses relay]
```

---

## Section 12 — Pre-Power Safety Checklist

Go through every item before plugging anything in:

- [ ] Every component has a wire going to the `−` (GND) rail
- [ ] DHT22, soil sensor, and float switch are all on 3.3V — **not** 5V
- [ ] Both relay modules are on 5V — **not** 3.3V
- [ ] No GPIO pins have bare wires that could touch each other or a power rail
- [ ] Pump and fan `−` wires run directly back to their own supply — not through a relay
- [ ] USB cable to the ESP32 is still unplugged
- [ ] Pump and fan power supplies are still unplugged

---

## Section 13 — First Power-On

**Step 1 — ESP32 only**
- [ ] Plug USB into the ESP32. The board LED should light up. If you smell burning, unplug immediately.

**Step 2 — Flash firmware**
- [ ] Flash MicroPython and all `.py` files from the `Firmware/` folder using Thonny or mpremote.

**Step 3 — Open serial monitor at 115200 baud**

Expected output:
```
WiFi connected: 192.168.x.x
NTP synced: 2026-06-03 ...
MQTT connected — subscribed to commands/greenhouse/esp32-gh-01
Telemetry: {"header": {...}, "payload": {"temperature": 24.5, "humidity": 58.0, ...}}
```

**Step 4 — Verify sensors**
- [ ] `temperature` and `humidity` show real numbers (not `null`, not 0)
- [ ] `soil_moisture` shows a number between 0 and 100
- [ ] `water_level` shows `0` when the float switch is shorted (water present) and `1` when open (tank empty)

**Step 5 — Connect pump and fan supplies**
- [ ] Only after sensor readings look correct, plug in the pump and fan supplies
- [ ] Send a `PUMP_ON` command via the backend — you should hear the relay click and the pump start
- [ ] Confirm that holding the float switch open (simulating an empty tank) prints `"Safety interlock: tank empty — PUMP_ON blocked"` and prevents the pump

---

## Section 14 — GPIO Quick-Reference

```
┌─────────────────────────────────────┐
│        ESP32-S2 GPIO MAP            │
│                                     │
│  GPIO 4  ──► DHT22 DATA             │
│  GPIO 5  ──► Pump Relay IN          │
│  GPIO 6  ──► Fan Relay IN           │
│  GPIO 7  ──► Float Switch (+ GND)   │
│  GPIO 10 ──► Soil Moisture AOUT     │
│                                     │
│  3V3  ──► DHT22 VCC                 │
│  3V3  ──► Soil Sensor VCC           │
│  5V   ──► Pump Relay VCC            │
│  5V   ──► Fan Relay VCC             │
│  GND  ──► Everything GND            │
└─────────────────────────────────────┘
```

> GPIOs 26–32 are reserved for the embedded SPI flash on all ESP32-S2 modules and cannot be used as user GPIO.
