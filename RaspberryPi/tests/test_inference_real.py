"""
Real integration tests for vision_agent._run_inference().

These tests call the actual Roboflow Strawberry Detect model via the inference SDK.
They are skipped unless RPI_REAL=1 is set in the environment.

Prerequisites:
  - Install dependencies: pip install inference paho-mqtt
  - Set ROBOFLOW_API_KEY in config.py (or override via env var)
  - Provide a test image: set RPI_TEST_IMAGE=/path/to/strawberry.jpg

Typical usage on the Pi:
  RPI_REAL=1 RPI_TEST_IMAGE=/home/pi/test.jpg pytest RaspberryPi/tests/test_inference_real.py -v
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest

_SKIP_REASON = "Set RPI_REAL=1 (and provide RPI_TEST_IMAGE) to run real Roboflow inference tests"
pytestmark = pytest.mark.skipif(not os.getenv("RPI_REAL"), reason=_SKIP_REASON)


@pytest.fixture(scope="module")
def real_vision_agent():
    """
    Import vision_agent using the real inference SDK (not the conftest mock).

    Removes any stub from sys.modules so the genuine Roboflow package is used.
    """
    for key in list(sys.modules):
        if key in ("inference", "vision_agent"):
            del sys.modules[key]

    import vision_agent as va
    yield va

    # Restore stubs so other test files aren't affected
    for key in ("inference", "vision_agent"):
        sys.modules.pop(key, None)


@pytest.fixture(scope="module")
def real_model(real_vision_agent):
    """Load the Roboflow Strawberry Detect model once per test session."""
    return real_vision_agent._load_model()


@pytest.fixture
def test_image_path() -> str:
    path = os.getenv("RPI_TEST_IMAGE", "")
    if not path or not os.path.isfile(path):
        pytest.skip(f"RPI_TEST_IMAGE must point to an existing image file (got: {path!r})")
    return path


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.real
def test_real_inference_returns_expected_keys(real_model, test_image_path, real_vision_agent) -> None:
    result = real_vision_agent._run_inference(real_model, test_image_path)

    required = {"stage", "green_pct", "white_pink_pct", "red_pct", "confidence"}
    assert required.issubset(result.keys()), f"Missing keys in result: {result}"


@pytest.mark.real
def test_real_inference_stage_is_valid_plant_stage(real_model, test_image_path, real_vision_agent) -> None:
    result = real_vision_agent._run_inference(real_model, test_image_path)

    valid_stages = {"Green", "WhitePink", "Red"}
    assert result["stage"] in valid_stages, f"Unexpected stage: {result['stage']}"


@pytest.mark.real
def test_real_inference_percentages_are_in_range(real_model, test_image_path, real_vision_agent) -> None:
    result = real_vision_agent._run_inference(real_model, test_image_path)

    for key in ("green_pct", "white_pink_pct", "red_pct"):
        assert 0.0 <= result[key] <= 100.0, f"{key} out of range: {result[key]}"


@pytest.mark.real
def test_real_inference_confidence_is_in_range(real_model, test_image_path, real_vision_agent) -> None:
    result = real_vision_agent._run_inference(real_model, test_image_path)

    assert 0.0 <= result["confidence"] <= 1.0, f"confidence out of range: {result['confidence']}"


@pytest.mark.real
def test_real_inference_percentages_sum_correctly(real_model, test_image_path, real_vision_agent) -> None:
    result = real_vision_agent._run_inference(real_model, test_image_path)

    total = result["green_pct"] + result["white_pink_pct"] + result["red_pct"]
    # Floating-point rounding — allow up to 0.2 % drift
    assert abs(total - 100.0) < 0.2 or total == 0.0, f"Percentages don't sum to 100: {total}"
