# WiFi
# Wokwi simulation: use "Wokwi-GUEST" / ""
# Real hardware:    use your actual SSID / password
WIFI_SSID = "EdimaxAPf0"
WIFI_PASSWORD = "h9700156"

# MQTT broker — must match MQTT_BROKER_IP in Backend/.env
# Wokwi simulation (VS Code extension): "host.wokwi.internal" reaches localhost
# Real hardware: set to your broker's LAN IP (e.g. "192.168.1.100")
MQTT_BROKER = "10.0.0.13"
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
