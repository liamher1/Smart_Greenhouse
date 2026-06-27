"""
Build a combined ESP32-S2 flash image:
  0x0000  : zeros (padding before bootloader)
  0x1000  : MicroPython binary  (esp32s2-micropython.bin)
  0x200000: LittleFS filesystem (all .py files from this directory)

Run from the Firmware/ directory:
  python build_flash_image.py
Output: esp32s2-combined.bin  (load at flash address 0x0 in Wokwi)
"""

import os
import pathlib
import struct
import littlefs

FIRMWARE_DIR = pathlib.Path(__file__).parent
OUTPUT_BIN   = FIRMWARE_DIR / "esp32s2-combined.bin"
MICROPYTHON  = FIRMWARE_DIR / "esp32s2-micropython.bin"

# Flash layout constants (4 MB device)
FLASH_SIZE     = 4 * 1024 * 1024        # 4 MB total
FS_START       = 0x200000               # filesystem starts at 2 MB
FS_SIZE        = FLASH_SIZE - FS_START  # 2 MB for LittleFS
BLOCK_SIZE     = 4096                   # LittleFS block size = one erase sector
BINARY_OFFSET  = 0x1000                 # MicroPython binary flashed at 0x1000

# Files to inject into the filesystem (name-in-fs -> host path)
FILES = {
    "boot.py":              FIRMWARE_DIR / "boot.py",
    "main.py":              FIRMWARE_DIR / "main.py",
    "config.py":            FIRMWARE_DIR / "config.py",
    "dht_sensor.py":        FIRMWARE_DIR / "dht_sensor.py",
    "soil_sensor.py":       FIRMWARE_DIR / "soil_sensor.py",
    "float_switch.py":      FIRMWARE_DIR / "float_switch.py",
    "relay_board.py":       FIRMWARE_DIR / "relay_board.py",
    "pump.py":              FIRMWARE_DIR / "pump.py",
    "fan.py":               FIRMWARE_DIR / "fan.py",
    "mqtt_client.py":       FIRMWARE_DIR / "mqtt_client.py",
    "ntp_sync.py":          FIRMWARE_DIR / "ntp_sync.py",
    "lib/umqtt/__init__.py":FIRMWARE_DIR / "lib" / "umqtt" / "__init__.py",
    "lib/umqtt/simple.py":  FIRMWARE_DIR / "lib" / "umqtt" / "simple.py",
    "lib/umqtt/robust.py":  FIRMWARE_DIR / "lib" / "umqtt" / "robust.py",
}


def make_littlefs_image() -> bytes:
    block_count = FS_SIZE // BLOCK_SIZE
    fs = littlefs.LittleFS(block_size=BLOCK_SIZE, block_count=block_count)

    for fs_path, host_path in FILES.items():
        # Create parent directories if needed (ignore already-exists errors)
        if "/" in fs_path:
            parts = fs_path.split("/")[:-1]
            for depth in range(1, len(parts) + 1):
                d = "/".join(parts[:depth])
                try:
                    fs.mkdir(d)
                except FileExistsError:
                    pass

        content = host_path.read_bytes()
        with fs.open(fs_path, "wb") as f:
            f.write(content)
        print(f"  + {fs_path} ({len(content)} bytes)")

    return bytes(fs.context.buffer)


def build():
    print("Reading MicroPython binary...")
    fw = MICROPYTHON.read_bytes()
    print(f"  {len(fw):,} bytes")

    print("\nBuilding LittleFS image...")
    fs_image = make_littlefs_image()
    print(f"  {len(fs_image):,} bytes ({FS_SIZE // 1024} KB partition)")

    print("\nAssembling combined flash image...")
    flash = bytearray(FLASH_SIZE)

    # Place MicroPython binary at 0x1000
    flash[BINARY_OFFSET : BINARY_OFFSET + len(fw)] = fw

    # Place LittleFS at 0x200000
    flash[FS_START : FS_START + len(fs_image)] = fs_image

    OUTPUT_BIN.write_bytes(flash)
    print(f"\nWrote {OUTPUT_BIN} ({len(flash) // 1024} KB)")
    print("\nUpdate wokwi.toml:")
    print('  firmware = "esp32s2-combined.bin"')
    print("  # no elf needed — full flash image at offset 0x0")


if __name__ == "__main__":
    build()
