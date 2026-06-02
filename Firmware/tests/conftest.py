from __future__ import annotations

import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
from contextlib import suppress

import pytest

import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

FIRMWARE_DIR = pathlib.Path(__file__).parent.parent

_WOKWI_FALLBACK_PATHS = [
    pathlib.Path.home() / ".wokwi" / "bin" / "wokwi-cli.exe",
    pathlib.Path.home() / ".wokwi" / "bin" / "wokwi-cli",
]

FLASH_SIZE = 4 * 1024 * 1024
FS_START   = 0x200000
FS_SIZE    = FLASH_SIZE - FS_START
BLOCK_SIZE = 4096
BIN_OFFSET = 0x1000


def _find_wokwi_cli() -> str | None:
    found = shutil.which("wokwi-cli")
    if found:
        return found
    for p in _WOKWI_FALLBACK_PATHS:
        if p.exists():
            return str(p)
    return None


# ── guards ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def require_wokwi_cli():
    """Guard: wokwi-cli must be installed and authenticated."""
    if _find_wokwi_cli() is None:
        pytest.skip("wokwi-cli not installed — run: npm install -g @wokwi/cli")
    home = pathlib.Path.home()
    token_paths = [
        home / ".wokwi" / "token",
        home / ".config" / "wokwi" / "token",
    ]
    has_token = bool(os.environ.get("WOKWI_CLI_TOKEN")) or any(p.exists() for p in token_paths)
    if not has_token:
        pytest.skip("Wokwi token not found — set WOKWI_CLI_TOKEN or run 'wokwi-cli login'")


# ── flash image builder ───────────────────────────────────────────────────────

def _build_combined_image(
    target_dir: pathlib.Path,
    diagram: dict | None = None,
) -> None:
    """Write wokwi.toml, diagram.json, and a combined flash image into target_dir."""
    import littlefs

    target_dir.mkdir(parents=True, exist_ok=True)

    py_files: dict[str, bytes] = {}
    for name in ("boot.py", "main.py", "dht_sensor.py", "soil_sensor.py",
                 "float_switch.py", "pump.py", "fan.py",
                 "mqtt_client.py", "ntp_sync.py", "config.py"):
        py_files[name] = (FIRMWARE_DIR / name).read_bytes()

    for name in ("__init__.py", "simple.py", "robust.py"):
        py_files[f"lib/umqtt/{name}"] = (FIRMWARE_DIR / "lib" / "umqtt" / name).read_bytes()

    block_count = FS_SIZE // BLOCK_SIZE
    fs = littlefs.LittleFS(block_size=BLOCK_SIZE, block_count=block_count)
    for fs_path, content in py_files.items():
        if "/" in fs_path:
            parts = fs_path.split("/")[:-1]
            for depth in range(1, len(parts) + 1):
                d = "/".join(parts[:depth])
                try:
                    fs.mkdir(d)
                except FileExistsError:
                    pass
        with fs.open(fs_path, "wb") as f:
            f.write(content)
    fs_image = bytes(fs.context.buffer)

    flash = bytearray(FLASH_SIZE)
    fw = (FIRMWARE_DIR / "esp32s2-micropython.bin").read_bytes()
    flash[BIN_OFFSET : BIN_OFFSET + len(fw)] = fw
    flash[FS_START   : FS_START   + len(fs_image)] = fs_image
    (target_dir / "esp32s2-combined.bin").write_bytes(flash)

    (target_dir / "wokwi.toml").write_text(
        '[wokwi]\nversion = 1\nfirmware = "esp32s2-combined.bin"\n'
    )

    if diagram is None:
        shutil.copy2(FIRMWARE_DIR / "diagram.json", target_dir / "diagram.json")
    else:
        (target_dir / "diagram.json").write_text(json.dumps(diagram, indent=2))


# ── wokwi subprocess helpers ──────────────────────────────────────────────────

def _launch_wokwi(
    fw_dir: pathlib.Path,
    serial_log: pathlib.Path,
    timeout_ms: int = 120_000,
    interactive: bool = False,
) -> subprocess.Popen:
    cli = _find_wokwi_cli()
    cmd = [cli, "--timeout", str(timeout_ms), "--serial-log-file", str(serial_log), str(fw_dir)]
    if interactive:
        cmd.insert(1, "--interactive")
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if interactive else subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="module")
def wokwi_process(tmp_path_factory, require_wokwi_cli):
    """Standard diagram — boot, telemetry, and command tests (no broker needed)."""
    fw_dir = tmp_path_factory.mktemp("fw")
    _build_combined_image(fw_dir)
    serial_log = fw_dir / "serial.log"

    proc = _launch_wokwi(fw_dir, serial_log)
    yield proc, serial_log

    proc.terminate()
    with suppress(Exception):
        proc.wait(timeout=5)


# DHT22 at 200°C — triggers ValueError in dht_sensor.read() on every reading
_DIAGRAM_DHT_OVERRANGE: dict = {
    "version": 1,
    "author": "Smart Greenhouse",
    "editor": "wokwi",
    "parts": [
        {"type": "board-esp32-s2-devkitm-1", "id": "esp",  "top": 0,   "left": 0,   "attrs": {}},
        {"type": "wokwi-dht22",              "id": "dht1", "top": -60, "left": 200,
         "attrs": {"temperature": "200", "humidity": "62"}},
        {"type": "wokwi-resistor",           "id": "r1",    "top": 110, "left": 245, "attrs": {"value": "220"}},
        {"type": "wokwi-led",                "id": "led1",  "top": 90,  "left": 310,
         "attrs": {"color": "blue", "label": "Pump relay"}},
        {"type": "wokwi-pushbutton",         "id": "btn1",  "top": -60, "left": 370,
         "attrs": {"label": "Float switch"}},
    ],
    "connections": [
        ["esp:4",    "dht1:SDA",          "green",  []],
        ["esp:3V3",  "dht1:VCC",          "red",    []],
        ["esp:GND.1","dht1:GND",          "black",  []],
        ["esp:5",    "r1:1",              "orange", []],
        ["r1:2",     "led1:A",            "orange", []],
        ["esp:GND.1","led1:C",            "black",  []],
        ["esp:7",    "btn1:1.l",          "yellow", []],
        ["esp:GND.1","btn1:2.l",          "black",  []],
        ["esp:TX",   "$serialMonitor:RX", "",       []],
        ["esp:RX",   "$serialMonitor:TX", "",       []],
    ],
}


@pytest.fixture(scope="module")
def wokwi_error_process(tmp_path_factory, require_wokwi_cli):
    """DHT22 at 200°C — triggers ValueError on every sensor read."""
    fw_dir = tmp_path_factory.mktemp("fw_error")
    _build_combined_image(fw_dir, diagram=_DIAGRAM_DHT_OVERRANGE)
    serial_log = fw_dir / "serial_error.log"

    proc = _launch_wokwi(fw_dir, serial_log, timeout_ms=90_000)
    yield proc, serial_log

    proc.terminate()
    with suppress(Exception):
        proc.wait(timeout=5)


@pytest.fixture(scope="module")
def wokwi_process_interactive(tmp_path_factory, require_wokwi_cli):
    """Standard diagram with --interactive: stdin is piped to the ESP32 REPL."""
    fw_dir = tmp_path_factory.mktemp("fw_interactive")
    _build_combined_image(fw_dir)
    serial_log = fw_dir / "serial.log"

    proc = _launch_wokwi(fw_dir, serial_log, timeout_ms=120_000, interactive=True)
    yield proc, serial_log

    proc.terminate()
    with suppress(Exception):
        proc.wait(timeout=5)
