"""
Shared pytest configuration for RaspberryPi vision agent tests.

Mocks hardware/cloud dependencies (picamera2, inference SDK, paho-mqtt) before
vision_agent is imported so the unit tests can run on any machine without Pi
hardware or a Roboflow API key.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add RaspberryPi root to path so `import vision_agent` and `import config` resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub out hardware/cloud packages — must happen before vision_agent is imported
sys.modules.setdefault("inference", MagicMock())
sys.modules.setdefault("paho", MagicMock())
sys.modules.setdefault("paho.mqtt", MagicMock())
sys.modules.setdefault("paho.mqtt.client", MagicMock())
sys.modules.setdefault("picamera2", MagicMock())
sys.modules.setdefault("picamera2.controls", MagicMock())


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "real: requires RPI_REAL=1 env var, a Roboflow API key, and a test image on disk",
    )
