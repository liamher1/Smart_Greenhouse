"""
Raspberry Pi vision agent — Strawberry Detect (Roboflow).

Captures an image every INFERENCE_INTERVAL_SEC, runs YOLOv8 inference using
the Roboflow Strawberry Detect model, maps detections to the three greenhouse
plant stages, then publishes results to the MQTT broker.

MQTT topic : greenhouse/vision/<DEVICE_ID>
Payload    : IncomingMqttDto envelope (matches Backend vision entrypoint)

Strawberry Detect class → PlantStage mapping:
  Flower           → Green  (pre-fruit, early stage)
  Green Strawberry → Green
  Red Strawberry   → Red
  (No White/Pink class — stage assigned "WhitePink" when neither dominates)
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from inference import get_model

import config

# ── Stage label constants — must match backend PlantStage enum values ─────────
_STAGE_GREEN     = "Green"
_STAGE_WHITEPINK = "WhitePink"
_STAGE_RED       = "Red"

# Roboflow model class names (lowercase) → stage bucket
_GREEN_CLASSES = {"flower", "green strawberry"}
_RED_CLASSES   = {"red strawberry"}


# ── Model ─────────────────────────────────────────────────────────────────────

def _load_model():
    """Download (first run) or load cached Roboflow model."""
    print(f"[Vision] Loading model '{config.MODEL_ID}' ...")
    model = get_model(model_id=config.MODEL_ID, api_key=config.ROBOFLOW_API_KEY)
    print("[Vision] Model ready.")
    return model


# ── Camera ────────────────────────────────────────────────────────────────────

def _capture_image() -> str:
    """Capture a still from the Pi Camera Module 3, save locally, return file path."""
    from picamera2 import Picamera2  # imported here — not available on non-Pi systems
    from picamera2.controls import AfModeEnum

    Path(config.IMAGE_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(config.IMAGE_SAVE_DIR, f"capture_{ts}.jpg")

    cam = Picamera2()
    cam.configure(cam.create_still_configuration())
    cam.start()

    # Camera Module 3 has autofocus — trigger a focus cycle before capture
    # so the inference model receives a sharp, well-focused image
    cam.set_controls({"AfMode": AfModeEnum.Auto})
    cam.autofocus_cycle()

    cam.capture_file(path)
    cam.stop()

    print(f"[Vision] Image saved: {path}")
    return path


# ── Inference ─────────────────────────────────────────────────────────────────

def _run_inference(model, image_path: str) -> dict:
    """
    Run the Strawberry Detect model and return a dict ready for the MQTT payload.

    Returns stage percentages and dominant stage:
      - green_pct      : % of detections that are Flower or Green Strawberry
      - red_pct        : % of detections that are Red Strawberry
      - white_pink_pct : residual (100 - green - red); non-zero when mixed
      - stage          : dominant PlantStage string
      - confidence     : average detection confidence (0–1)
    """
    results     = model.infer(image_path, confidence=config.CONFIDENCE_THRESHOLD)[0]
    predictions = results.predictions

    if not predictions:
        print("[Vision] No strawberries detected — reporting Green stage at 0% confidence.")
        return {
            "stage":          _STAGE_GREEN,
            "green_pct":      0.0,
            "white_pink_pct": 0.0,
            "red_pct":        0.0,
            "confidence":     0.0,
        }

    green_count = 0
    red_count   = 0
    total_conf  = 0.0

    for pred in predictions:
        cls = pred.class_name.lower()
        total_conf += pred.confidence
        if cls in _GREEN_CLASSES:
            green_count += 1
        elif cls in _RED_CLASSES:
            red_count += 1

    total     = green_count + red_count
    green_pct = round(green_count / total * 100, 1) if total else 0.0
    red_pct   = round(red_count   / total * 100, 1) if total else 0.0
    avg_conf  = round(total_conf / len(predictions), 3)

    # Stage assignment — WhitePink covers the transition window where neither
    # green nor red reaches the dominance threshold (e.g. 40 % green / 60 % red)
    if red_pct >= config.DOMINANCE_THRESHOLD_PCT:
        stage = _STAGE_RED
    elif green_pct >= config.DOMINANCE_THRESHOLD_PCT:
        stage = _STAGE_GREEN
    else:
        stage = _STAGE_WHITEPINK

    # Residual percentage: non-zero only when both classes are detected (mixed frame)
    white_pink_pct = round(max(0.0, 100.0 - green_pct - red_pct), 1)

    return {
        "stage":          stage,
        "green_pct":      green_pct,
        "white_pink_pct": white_pink_pct,
        "red_pct":        red_pct,
        "confidence":     avg_conf,
    }


# ── MQTT ──────────────────────────────────────────────────────────────────────

def _connect_mqtt() -> mqtt.Client:
    client = mqtt.Client(client_id=f"{config.DEVICE_ID}-vision")

    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print(f"[Vision] MQTT disconnected (rc={rc}), reconnecting...")
            _reconnect(client)

    client.on_disconnect = on_disconnect
    _reconnect(client)
    client.loop_start()
    return client


def _reconnect(client: mqtt.Client) -> None:
    delay = 2
    while True:
        try:
            client.connect(config.MQTT_BROKER, config.MQTT_PORT)
            print(f"[Vision] MQTT connected to {config.MQTT_BROKER}:{config.MQTT_PORT}")
            return
        except Exception as e:
            print(f"[Vision] MQTT connect failed: {e} — retrying in {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 60)


def _publish(client: mqtt.Client, inference_result: dict) -> None:
    topic = f"greenhouse/vision/{config.DEVICE_ID}"
    message = {
        "header": {
            "type":      "vision",
            "device_id": config.DEVICE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "payload": inference_result,
    }
    client.publish(topic, json.dumps(message), qos=1)
    print(f"[Vision] Published → {topic} | stage={inference_result['stage']} "
          f"green={inference_result['green_pct']}% "
          f"red={inference_result['red_pct']}% "
          f"conf={inference_result['confidence']}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("[Vision] Agent starting.")
    model  = _load_model()
    client = _connect_mqtt()

    # Trigger immediately on first boot, then respect the interval
    last_run = time.time() - config.INFERENCE_INTERVAL_SEC

    while True:
        if time.time() - last_run >= config.INFERENCE_INTERVAL_SEC:
            try:
                image_path       = _capture_image()
                inference_result = _run_inference(model, image_path)
                _publish(client, inference_result)
            except Exception as e:
                print(f"[Vision] Cycle error: {e}")
            finally:
                last_run = time.time()

        time.sleep(10)


if __name__ == "__main__":
    main()
