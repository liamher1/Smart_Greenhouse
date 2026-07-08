"""
Raspberry Pi vision agent — Strawberry Detect (Roboflow serverless API).

Captures an image every INFERENCE_INTERVAL_SEC, runs inference via Roboflow's
serverless hosted API (no local model, no PyTorch dependency), maps detections
to the three greenhouse plant stages, then publishes results to the MQTT broker.

MQTT topic : greenhouse/vision/<DEVICE_ID>
Payload    : IncomingMqttDto envelope (matches Backend vision entrypoint)

Strawberry Detect class → PlantStage mapping:
  Flower           → Green  (pre-fruit, early stage)
  Green Strawberry → Green
  Red Strawberry   → Red
  (WhitePink when neither green nor red reaches the dominance threshold)
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import base64

import requests
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

import config

# ── Stage label constants — must match backend PlantStage enum values ─────────
_STAGE_GREEN     = "Green"
_STAGE_WHITEPINK = "WhitePink"
_STAGE_RED       = "Red"

# Roboflow class names (lowercase) → stage bucket
_GREEN_CLASSES = {"flower", "green strawberry"}
_RED_CLASSES   = {"red strawberry"}


# ── Roboflow client ───────────────────────────────────────────────────────────

def _load_model() -> None:
    if not config.ROBOFLOW_API_KEY:
        raise RuntimeError("ROBOFLOW_API_KEY is not set in RaspberryPi/.env")
    print(f"[Vision] Roboflow serverless API ready (model: {config.MODEL_ID})")


# ── Camera ────────────────────────────────────────────────────────────────────

def _capture_image() -> str:
    """Capture a still via rpicam-still CLI, save locally, return file path."""
    Path(config.IMAGE_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(config.IMAGE_SAVE_DIR, f"capture_{ts}.jpg")

    result = subprocess.run(
        [
            "rpicam-still",
            "--output", path,
            "--autofocus-mode", "auto",
            "--timeout", "3000",
            "--nopreview",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"rpicam-still failed: {result.stderr.strip()}")

    print(f"[Vision] Image saved: {path}")
    return path


# ── Inference ─────────────────────────────────────────────────────────────────

def _run_inference(image_path: str) -> dict:
    """
    Send image to Roboflow and return stage stats.

    Returns:
      - stage          : dominant PlantStage string (Green / WhitePink / Red)
      - green_pct      : % of detections that are Flower or Green Strawberry
      - white_pink_pct : residual (100 - green - red)
      - red_pct        : % of detections that are Red Strawberry
      - confidence     : average detection confidence (0–1)
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    resp = requests.post(
        f"https://serverless.roboflow.com/{config.MODEL_ID}",
        params={"api_key": config.ROBOFLOW_API_KEY},
        data=image_b64,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    predictions = resp.json().get("predictions", [])

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
        cls = pred["class"].lower()
        total_conf += pred["confidence"]
        if cls in _GREEN_CLASSES:
            green_count += 1
        elif cls in _RED_CLASSES:
            red_count += 1

    total     = green_count + red_count
    green_pct = round(green_count / total * 100, 1) if total else 0.0
    red_pct   = round(red_count   / total * 100, 1) if total else 0.0
    avg_conf  = round(total_conf / len(predictions), 3)

    if red_pct >= config.DOMINANCE_THRESHOLD_PCT:
        stage = _STAGE_RED
    elif green_pct >= config.DOMINANCE_THRESHOLD_PCT:
        stage = _STAGE_GREEN
    else:
        stage = _STAGE_WHITEPINK

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
    client = mqtt.Client(CallbackAPIVersion.VERSION1, client_id=f"{config.DEVICE_ID}-vision")
    client.reconnect_delay_set(min_delay=2, max_delay=60)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"[Vision] MQTT connected to {config.MQTT_BROKER}:{config.MQTT_PORT}")
        else:
            print(f"[Vision] MQTT connect failed rc={rc}")

    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print(f"[Vision] MQTT disconnected (rc={rc}), will auto-reconnect...")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    while True:
        try:
            client.connect(config.MQTT_BROKER, config.MQTT_PORT)
            break
        except Exception as e:
            print(f"[Vision] MQTT connect failed: {e} — retrying in 5s")
            time.sleep(5)

    client.loop_start()
    return client


def _publish(client: mqtt.Client, inference_result: dict) -> None:
    topic   = f"greenhouse/vision/{config.DEVICE_ID}"
    message = {
        "header": {
            "type":      "vision",
            "device_id": config.DEVICE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "payload": inference_result,
    }
    client.publish(topic, json.dumps(message), qos=1)
    print(
        f"[Vision] Published → {topic} | stage={inference_result['stage']} "
        f"green={inference_result['green_pct']}% "
        f"red={inference_result['red_pct']}% "
        f"conf={inference_result['confidence']}"
    )


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("[Vision] Agent starting.")
    _load_model()
    mqtt_client = _connect_mqtt()

    last_run = time.time() - config.INFERENCE_INTERVAL_SEC

    while True:
        if time.time() - last_run >= config.INFERENCE_INTERVAL_SEC:
            try:
                image_path       = _capture_image()
                inference_result = _run_inference(image_path)
                _publish(mqtt_client, inference_result)
            except Exception as e:
                print(f"[Vision] Cycle error: {e}")
            finally:
                last_run = time.time()

        time.sleep(10)


if __name__ == "__main__":
    main()
