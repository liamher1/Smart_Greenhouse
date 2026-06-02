# Raspberry Pi Slice (Vision Agent)

## Purpose

The Raspberry Pi is the greenhouse hub. It runs the Mosquitto MQTT broker (shared by all devices) and hosts the Vision Agent — a Python process that periodically captures an image with the Camera Module 3, runs Strawberry Detect YOLOv8 inference locally via the Roboflow `inference` SDK, maps detections to the three `PlantStage` values, and publishes results to the MQTT broker so the Backend's Vision slice can consume them.

## Files

| File | Role |
|---|---|
| `RaspberryPi/config.py` | Device ID, MQTT settings, inference interval, Roboflow model ID |
| `RaspberryPi/vision_agent.py` | Main loop: capture → autofocus → infer → map stages → publish |
| `RaspberryPi/requirements.txt` | `inference`, `paho-mqtt`, `picamera2` |
| `RaspberryPi/vision-agent.service` | systemd unit — auto-starts agent on Pi boot |

## Model

**Roboflow Strawberry Detect**
- Universe page: `universe.roboflow.com/strawberries/strawberry-detect`
- Model ID: `strawberry-detect/1`
- Classes: `Flower`, `Green Strawberry`, `Red Strawberry`
- Downloaded and cached locally on first run; subsequent runs are fully offline.

## Class → PlantStage Mapping

| Detected class | Maps to |
|---|---|
| `Flower` | `Green` (pre-fruit, early vegetative) |
| `Green Strawberry` | `Green` |
| `Red Strawberry` | `Red` |
| Neither dominates (< 60 % each) | `WhitePink` (transitioning) |

`white_pink_pct` is computed as the residual: `100 - green_pct - red_pct`. It is non-zero when both green and red detections appear in the same frame.

## Inference Pipeline

```
Every INFERENCE_INTERVAL_SEC (default: 4 hours)

1. Picamera2.start()
2. Set AfMode = Auto  (Camera Module 3 autofocus)
3. autofocus_cycle()  → sharp focus on fruit
4. capture_file(path) → save JPEG locally to /home/pi/greenhouse/images/
5. Picamera2.stop()

6. model.infer(path, confidence=0.40)
   → list of predictions: class_name + confidence score

7. Count per bucket:
     green_count = Flower + Green Strawberry detections
     red_count   = Red Strawberry detections
     total       = green_count + red_count

8. Compute:
     green_pct      = green_count / total * 100
     red_pct        = red_count   / total * 100
     white_pink_pct = 100 - green_pct - red_pct
     avg_confidence = mean(all detection confidences)

9. Assign stage:
     red_pct   >= 60 %  →  "Red"
     green_pct >= 60 %  →  "Green"
     otherwise          →  "WhitePink"

10. Publish MQTT message
```

## MQTT Output

**Topic:** `greenhouse/vision/rpi-gh-01`

**Payload:**

```json
{
  "header": {
    "type": "vision",
    "device_id": "rpi-gh-01",
    "timestamp": "2026-06-02T10:00:00+00:00"
  },
  "payload": {
    "stage": "Red",
    "green_pct": 10.5,
    "white_pink_pct": 0.0,
    "red_pct": 89.5,
    "confidence": 0.87
  }
}
```

## Connection Resilience

MQTT reconnect uses exponential backoff: starts at 2 s, doubles each failure, caps at 60 s. The `paho-mqtt` `on_disconnect` callback triggers reconnect automatically on drop.

## Deployment on Pi

```bash
# 1. Clone and install dependencies
pip install -r RaspberryPi/requirements.txt

# 2. Set your Roboflow API key in config.py
#    ROBOFLOW_API_KEY = "your_key_here"
#    (Free key at https://app.roboflow.com)

# 3. First run — downloads and caches model (needs internet once)
python RaspberryPi/vision_agent.py

# 4. Install as a system service (auto-start on boot)
sudo cp RaspberryPi/vision-agent.service /etc/systemd/system/
sudo systemctl enable --now vision-agent

# Check logs
journalctl -u vision-agent -f
```

## Configuration Reference (`config.py`)

| Key | Default | Description |
|---|---|---|
| `DEVICE_ID` | `"rpi-gh-01"` | Published in MQTT header; must match backend expectations |
| `MQTT_BROKER` | `"localhost"` | Pi is the broker |
| `MQTT_PORT` | `1883` | Standard MQTT port |
| `INFERENCE_INTERVAL_SEC` | `14400` (4 h) | How often to capture and infer |
| `ROBOFLOW_API_KEY` | `""` | **Required** — set before first run |
| `MODEL_ID` | `"strawberry-detect/1"` | Check version on Roboflow Universe |
| `CONFIDENCE_THRESHOLD` | `0.40` | Minimum score to count a detection |
| `DOMINANCE_THRESHOLD_PCT` | `60.0` | % needed to assign Green or Red stage |
| `IMAGE_SAVE_DIR` | `/home/pi/greenhouse/images` | Local image archive |

## No-Detection Handling

If the model detects zero strawberries (early growth, occlusion, bad lighting):

```json
{
  "stage": "Green",
  "green_pct": 0.0,
  "white_pink_pct": 0.0,
  "red_pct": 0.0,
  "confidence": 0.0
}
```

Confidence = 0.0 signals to consumers that no fruit was detected. The backend will still update `GreenhouseState` to `Green` (safe default — most permissive irrigation).
