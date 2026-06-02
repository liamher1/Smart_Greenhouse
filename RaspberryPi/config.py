DEVICE_ID = "rpi-gh-01"

# MQTT — Pi is the broker, so this is localhost
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# How often to capture and run inference (seconds)
# Architecture target: every 4-6 hours to balance resource use and accuracy
INFERENCE_INTERVAL_SEC = 4 * 3600  # 4 hours

# Roboflow Strawberry Detect model
# Get a free API key at https://app.roboflow.com
# Model page: https://universe.roboflow.com/strawberries/strawberry-detect
# Check the version number on the model page and update below if needed
ROBOFLOW_API_KEY = ""
MODEL_ID = "strawberry-detect/1"

# Minimum confidence to count a detection (0.0 – 1.0)
CONFIDENCE_THRESHOLD = 0.40

# Dominant stage threshold — stage is assigned when one class exceeds this %
DOMINANCE_THRESHOLD_PCT = 60.0

# Directory where captured images are stored locally on the Pi
IMAGE_SAVE_DIR = "/home/pi/greenhouse/images"
