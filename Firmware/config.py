# WiFi
WIFI_SSID = "your_ssid"
WIFI_PASSWORD = "your_password"

# MQTT broker — must match MQTT_BROKER_IP in Backend/.env
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883

# Unique identifier for this device — used in MQTT topics and telemetry headers
DEVICE_ID = "esp32-gh-01"

# How often telemetry is published (seconds)
TELEMETRY_INTERVAL_S = 30

# GPIO pin connected to the DHT22 data line
DHT_PIN = 4

# GPIO pin connected to the relay IN pin
# Set PUMP_ACTIVE_HIGH = True  if relay triggers on HIGH (most 5V relay modules)
# Set PUMP_ACTIVE_HIGH = False if relay triggers on LOW  (active-low relay boards)
PUMP_PIN = 5
PUMP_ACTIVE_HIGH = True
