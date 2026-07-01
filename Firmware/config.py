# WiFi
# Wokwi simulation: use "Wokwi-GUEST" / ""
# Real hardware:    use your actual SSID / password
WIFI_SSID = "Greenhouse"
WIFI_PASSWORD = "greenhouse2024"

# MQTT broker — Raspberry Pi hotspot IP (fixed by hostapd/NetworkManager)
MQTT_BROKER = "192.168.4.1"
MQTT_PORT = 1883

# Unique identifier for this device — used in MQTT topics and telemetry headers
DEVICE_ID = "esp32-gh-01"

# MQTT topics
MQTT_COMMAND_TOPIC = f"commands/greenhouse/{DEVICE_ID}"

# How often telemetry is published (seconds)
# Wokwi simulation: 5 for fast feedback; real hardware: 900 (15 min)
TELEMETRY_INTERVAL_SEC = 900

# GPIO pin connected to the DHT22 data line
DHT_PIN = 4

# Soil moisture sensor (analog ADC input)
# ESP32-S2 ADC is only on GPIO 1-20; GPIO 34 (original ESP32) is NOT valid here.
SOIL_MOISTURE_PIN = 10

# Capacitive soil moisture sensor calibration (raw ADC 0–4095).
# Measure your sensor in dry air and in water to find your values.
# Default: typical values for a generic capacitive sensor.
SOIL_ADC_DRY = 3200   # ADC reading in completely dry soil / air
SOIL_ADC_WET = 1100   # ADC reading in saturated / submerged soil

# Seeed Studio Multi-Channel I2C Relay Board
I2C_SDA_PIN = 1
I2C_SCL_PIN = 2
RELAY_I2C_ADDR = 0x11

PUMP_RELAY_CHANNEL = 3
FAN_RELAY_CHANNEL = 2

# Water level float switch (digital input, active-LOW when water present)
FLOAT_SWITCH_PIN = 7
