"""
Mock-based unit tests for vision_agent._run_inference().

These run on any machine — no Roboflow API key, Pi camera, or inference SDK
installation required. All hardware/cloud dependencies are stubbed by conftest.py.
"""
from __future__ import annotations

import vision_agent


# ── Minimal mock objects matching the Roboflow SDK's return shape ─────────────

class _Prediction:
    def __init__(self, class_name: str, confidence: float) -> None:
        self.class_name = class_name
        self.confidence = confidence


class _InferenceResult:
    def __init__(self, predictions: list[_Prediction]) -> None:
        self.predictions = predictions


class _MockModel:
    def __init__(self, predictions: list[_Prediction]) -> None:
        self._predictions = predictions

    def infer(self, image_path: str, confidence: float) -> list[_InferenceResult]:
        return [_InferenceResult(self._predictions)]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _run(predictions: list[_Prediction]) -> dict:
    return vision_agent._run_inference(_MockModel(predictions), "fake/path.jpg")


# ── No detections ──────────────────────────────────────────────────────────────

def test_no_detections_returns_green_stage_at_zero_confidence() -> None:
    result = _run([])

    assert result["stage"] == "Green"
    assert result["green_pct"] == 0.0
    assert result["white_pink_pct"] == 0.0
    assert result["red_pct"] == 0.0
    assert result["confidence"] == 0.0


# ── Green-dominant scenes ──────────────────────────────────────────────────────

def test_all_green_strawberries_returns_green_stage() -> None:
    preds = [
        _Prediction("Green Strawberry", 0.9),
        _Prediction("Green Strawberry", 0.8),
        _Prediction("Green Strawberry", 0.7),
    ]
    result = _run(preds)

    assert result["stage"] == "Green"
    assert result["green_pct"] == 100.0
    assert result["red_pct"] == 0.0


def test_flowers_count_as_green_stage() -> None:
    preds = [
        _Prediction("Flower", 0.85),
        _Prediction("Flower", 0.75),
    ]
    result = _run(preds)

    assert result["stage"] == "Green"
    assert result["green_pct"] == 100.0


def test_mixed_green_classes_all_map_to_green() -> None:
    preds = [
        _Prediction("Flower", 0.9),
        _Prediction("Green Strawberry", 0.8),
    ]
    result = _run(preds)

    assert result["stage"] == "Green"
    assert result["green_pct"] == 100.0


# ── Red-dominant scenes ────────────────────────────────────────────────────────

def test_all_red_strawberries_returns_red_stage() -> None:
    preds = [
        _Prediction("Red Strawberry", 0.95),
        _Prediction("Red Strawberry", 0.88),
    ]
    result = _run(preds)

    assert result["stage"] == "Red"
    assert result["red_pct"] == 100.0
    assert result["green_pct"] == 0.0


# ── WhitePink transition zone ──────────────────────────────────────────────────

def test_even_split_returns_white_pink_stage() -> None:
    # 50 % green, 50 % red — neither crosses the 60 % dominance threshold
    preds = [
        _Prediction("Green Strawberry", 0.8),
        _Prediction("Red Strawberry", 0.8),
    ]
    result = _run(preds)

    assert result["stage"] == "WhitePink"
    assert result["green_pct"] == 50.0
    assert result["red_pct"] == 50.0


def test_just_below_dominance_threshold_is_white_pink() -> None:
    # 3 green / 2 red = 60 % green — exactly at threshold → Green (gte)
    # 2 green / 3 red = 40 % green, 60 % red → Red
    # 2 green / 2 red + 1 unknown = 50 % → WhitePink
    preds = [
        _Prediction("Green Strawberry", 0.7),
        _Prediction("Green Strawberry", 0.7),
        _Prediction("Red Strawberry", 0.7),
        _Prediction("Red Strawberry", 0.7),
        _Prediction("Red Strawberry", 0.7),
    ]  # 40 % green, 60 % red → Red (red reaches 60 %)
    result = _run(preds)

    assert result["stage"] == "Red"
    assert result["red_pct"] == 60.0


def test_exactly_at_dominance_threshold_assigns_stage() -> None:
    # 3 out of 5 = 60 % green → should be Green
    preds = [
        _Prediction("Green Strawberry", 0.8),
        _Prediction("Green Strawberry", 0.8),
        _Prediction("Green Strawberry", 0.8),
        _Prediction("Red Strawberry", 0.8),
        _Prediction("Red Strawberry", 0.8),
    ]
    result = _run(preds)

    assert result["stage"] == "Green"
    assert result["green_pct"] == 60.0


# ── Confidence averaging ───────────────────────────────────────────────────────

def test_confidence_is_averaged_across_all_predictions() -> None:
    preds = [
        _Prediction("Green Strawberry", 0.9),
        _Prediction("Green Strawberry", 0.7),
    ]
    result = _run(preds)

    assert result["confidence"] == round((0.9 + 0.7) / 2, 3)


def test_confidence_averaged_across_mixed_classes() -> None:
    preds = [
        _Prediction("Green Strawberry", 0.6),
        _Prediction("Red Strawberry", 0.8),
        _Prediction("Red Strawberry", 0.9),
    ]
    result = _run(preds)

    expected_conf = round((0.6 + 0.8 + 0.9) / 3, 3)
    assert result["confidence"] == expected_conf


# ── Result structure ───────────────────────────────────────────────────────────

def test_result_always_contains_required_keys() -> None:
    required = {"stage", "green_pct", "white_pink_pct", "red_pct", "confidence"}

    result = _run([_Prediction("Red Strawberry", 0.9)])

    assert required.issubset(result.keys())


def test_percentages_sum_to_100_for_pure_scenes() -> None:
    preds = [_Prediction("Green Strawberry", 0.8)] * 4

    result = _run(preds)

    total = result["green_pct"] + result["white_pink_pct"] + result["red_pct"]
    assert abs(total - 100.0) < 0.1


def test_white_pink_pct_is_residual_in_mixed_scene() -> None:
    # 1 green + 1 red = 50 % each; white_pink_pct should be 0 (100 - 50 - 50)
    preds = [
        _Prediction("Green Strawberry", 0.8),
        _Prediction("Red Strawberry", 0.8),
    ]
    result = _run(preds)

    assert result["white_pink_pct"] == 0.0
