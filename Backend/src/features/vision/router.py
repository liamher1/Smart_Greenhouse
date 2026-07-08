from __future__ import annotations

import asyncio
import base64
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from base.infrastructure.database import get_session
from config import config

from .models import VisionReading
from .repository import VisionRepository

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])

_GREEN_CLASSES = {"flower", "green strawberry"}
_RED_CLASSES = {"red strawberry"}
_DOMINANCE = 60.0
_ROBOFLOW_MODEL = "strawberry-detect/6"


def _capture_and_infer() -> dict:
    if not os.getenv("ROBOFLOW_API_KEY") and not _get_roboflow_key():
        raise RuntimeError("ROBOFLOW_API_KEY not set")

    Path(config.IMAGE_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"capture_{ts}.jpg"
    path = os.path.join(config.IMAGE_SAVE_DIR, filename)

    result = subprocess.run(
        ["rpicam-still", "--output", path, "--autofocus-mode", "auto",
         "--timeout", "3000", "--nopreview"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"rpicam-still failed: {result.stderr.strip()}")

    api_key = _get_roboflow_key()
    with open(path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    resp = http_requests.post(
        f"https://serverless.roboflow.com/{_ROBOFLOW_MODEL}",
        params={"api_key": api_key},
        data=image_b64,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    predictions = resp.json().get("predictions", [])

    if not predictions:
        return {
            "stage": "Green", "green_pct": 0.0,
            "white_pink_pct": 0.0, "red_pct": 0.0,
            "confidence": 0.0, "image_filename": filename,
        }

    green_count = red_count = 0
    total_conf = 0.0
    for pred in predictions:
        cls = pred["class"].lower()
        total_conf += pred["confidence"]
        if cls in _GREEN_CLASSES:
            green_count += 1
        elif cls in _RED_CLASSES:
            red_count += 1

    total = green_count + red_count
    green_pct = round(green_count / total * 100, 1) if total else 0.0
    red_pct = round(red_count / total * 100, 1) if total else 0.0
    avg_conf = round(total_conf / len(predictions), 3)

    if red_pct >= _DOMINANCE:
        stage = "Red"
    elif green_pct >= _DOMINANCE:
        stage = "Green"
    else:
        stage = "WhitePink"

    return {
        "stage": stage,
        "green_pct": green_pct,
        "white_pink_pct": round(max(0.0, 100.0 - green_pct - red_pct), 1),
        "red_pct": red_pct,
        "confidence": avg_conf,
        "image_filename": filename,
    }


def _get_roboflow_key() -> str:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[4] / "RaspberryPi" / ".env")
    key = os.getenv("ROBOFLOW_API_KEY", "")
    if not key:
        raise RuntimeError("ROBOFLOW_API_KEY not set in RaspberryPi/.env")
    return key


@router.get("/latest/{device_id}", status_code=status.HTTP_200_OK)
async def get_latest(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = VisionRepository(session)
    reading = await repo.get_latest(device_id)
    if reading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No vision readings found")
    return {
        "id": str(reading.id),
        "device_id": reading.device_id,
        "stage": reading.stage,
        "green_pct": reading.green_pct,
        "white_pink_pct": reading.white_pink_pct,
        "red_pct": reading.red_pct,
        "confidence": reading.confidence,
        "image_filename": reading.image_filename,
        "timestamp": reading.timestamp.isoformat(),
    }


@router.post("/capture/{device_id}", status_code=status.HTTP_200_OK)
async def capture_and_analyze(
    device_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        result = await asyncio.to_thread(_capture_and_infer)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Capture failed: {e}")

    from features.automation.models import PlantStage
    reading = VisionReading(
        device_id=device_id,
        stage=PlantStage(result["stage"]),
        green_pct=result["green_pct"],
        white_pink_pct=result["white_pink_pct"],
        red_pct=result["red_pct"],
        confidence=result["confidence"],
        image_filename=result["image_filename"],
    )
    repo = VisionRepository(session)
    await repo.add(reading)

    return {
        "id": str(reading.id),
        "device_id": reading.device_id,
        "stage": reading.stage,
        "green_pct": reading.green_pct,
        "white_pink_pct": reading.white_pink_pct,
        "red_pct": reading.red_pct,
        "confidence": reading.confidence,
        "image_filename": reading.image_filename,
        "timestamp": reading.timestamp.isoformat(),
    }
