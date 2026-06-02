"""
Albion Strawberry — database seed script.

Populates WateringPolicy and ControlRule rows derived from published
Albion strawberry greenhouse research:

  Temperature ranges   : Yake Climate / strawberry greenhouse guides
  Soil moisture targets: Deficit irrigation studies (40 % control → 20 % stress)
  Brix target          : 11–13° Brix at Red stage via pre-harvest water stress
  Humidity thresholds  : 40–75 % RH depending on stage (disease prevention)

Run from the repo root:
    python Backend/seeds/seed_albion.py
"""

import asyncio
import sys
from pathlib import Path

# Make Backend/src importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from base.infrastructure.database import async_session_maker, init_db
from features.automation.models import ControlRule, PlantStage, WateringPolicy


# ── Watering policies ─────────────────────────────────────────────────────────
# target_moisture : soil VWC % at which irrigation stops
# max_temperature : fan-on temperature ceiling for this stage

POLICIES: list[dict] = [
    {
        "plant_stage":     PlantStage.GREEN,
        "target_moisture": 30.0,   # generous moisture for vegetative growth
        "max_temperature": 24.0,   # 21–24°C optimal day temp (vegetative)
        "is_active":       True,
    },
    {
        "plant_stage":     PlantStage.WHITE_PINK,
        "target_moisture": 28.0,   # slightly drier to encourage fruit set
        "max_temperature": 21.0,   # 18–21°C optimal for pollination/flowering
        "is_active":       True,
    },
    {
        "plant_stage":     PlantStage.RED,
        "target_moisture": 20.0,   # water-stress deficit → Brix 11–13°
        "max_temperature": 27.0,   # 21–27°C optimal during ripening
        "is_active":       True,
    },
]


# ── Control rules ─────────────────────────────────────────────────────────────
# Each dict maps 1:1 to a ControlRule row.
# plant_stage = None  →  rule applies to ALL stages

RULES: list[dict] = [

    # ── GREEN STAGE ────────────────────────────────────────────────────────
    {
        "name":             "Green — irrigation ON",
        "plant_stage":      PlantStage.GREEN,
        "sensor_metric":    "soil_moisture",
        "operator":         "lt",
        "threshold":        30.0,
        "action":           "PUMP_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 5000,  # 5 s pulse; keeps soil evenly moist
    },
    {
        "name":             "Green — irrigation OFF",
        "plant_stage":      PlantStage.GREEN,
        "sensor_metric":    "soil_moisture",
        "operator":         "gt",
        "threshold":        35.0,   # hysteresis band: 30–35 %
        "action":           "PUMP_OFF",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "Green — fan ON (temp)",
        "plant_stage":      PlantStage.GREEN,
        "sensor_metric":    "temperature",
        "operator":         "gt",
        "threshold":        24.0,   # above vegetative optimum ceiling
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "Green — fan OFF (temp)",
        "plant_stage":      PlantStage.GREEN,
        "sensor_metric":    "temperature",
        "operator":         "lt",
        "threshold":        21.0,   # lower bound of vegetative optimum
        "action":           "FAN_OFF",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "Green — fan ON (humidity)",
        "plant_stage":      PlantStage.GREEN,
        "sensor_metric":    "humidity",
        "operator":         "gt",
        "threshold":        75.0,   # upper RH bound for vegetative stage
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },

    # ── WHITE/PINK STAGE (Flowering) ───────────────────────────────────────
    {
        "name":             "WhitePink — irrigation ON",
        "plant_stage":      PlantStage.WHITE_PINK,
        "sensor_metric":    "soil_moisture",
        "operator":         "lt",
        "threshold":        28.0,
        "action":           "PUMP_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 5000,
    },
    {
        "name":             "WhitePink — irrigation OFF",
        "plant_stage":      PlantStage.WHITE_PINK,
        "sensor_metric":    "soil_moisture",
        "operator":         "gt",
        "threshold":        33.0,   # hysteresis: 28–33 %
        "action":           "PUMP_OFF",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "WhitePink — fan ON (temp)",
        "plant_stage":      PlantStage.WHITE_PINK,
        "sensor_metric":    "temperature",
        "operator":         "gt",
        "threshold":        21.0,   # excess heat stalls/drops flowers
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "WhitePink — fan OFF (temp)",
        "plant_stage":      PlantStage.WHITE_PINK,
        "sensor_metric":    "temperature",
        "operator":         "lt",
        "threshold":        18.0,   # lower bound of flowering optimum
        "action":           "FAN_OFF",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "WhitePink — fan ON (humidity)",
        "plant_stage":      PlantStage.WHITE_PINK,
        "sensor_metric":    "humidity",
        "operator":         "gt",
        "threshold":        60.0,   # high RH during flowering → fungal risk
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },

    # ── RED STAGE (Ripening) ───────────────────────────────────────────────
    {
        "name":             "Red — irrigation ON (water stress)",
        "plant_stage":      PlantStage.RED,
        "sensor_metric":    "soil_moisture",
        "operator":         "lt",
        "threshold":        20.0,   # deliberate deficit → concentrates sugars (Brix 11–13°)
        "action":           "PUMP_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 3000,  # shorter pulse maintains stress regime
    },
    {
        "name":             "Red — irrigation OFF",
        "plant_stage":      PlantStage.RED,
        "sensor_metric":    "soil_moisture",
        "operator":         "gt",
        "threshold":        25.0,   # hysteresis: 20–25 %
        "action":           "PUMP_OFF",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "Red — fan ON (temp)",
        "plant_stage":      PlantStage.RED,
        "sensor_metric":    "temperature",
        "operator":         "gt",
        "threshold":        27.0,   # above ripening optimum ceiling
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "Red — fan OFF (temp)",
        "plant_stage":      PlantStage.RED,
        "sensor_metric":    "temperature",
        "operator":         "lt",
        "threshold":        24.0,   # lower bound of ripening optimum
        "action":           "FAN_OFF",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
    {
        "name":             "Red — fan ON (humidity)",
        "plant_stage":      PlantStage.RED,
        "sensor_metric":    "humidity",
        "operator":         "gt",
        "threshold":        70.0,   # high RH on ripe fruit → botrytis risk
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },

    # ── GLOBAL (all stages) ────────────────────────────────────────────────
    {
        "name":             "Global — emergency cooling",
        "plant_stage":      None,   # applies regardless of stage
        "sensor_metric":    "temperature",
        "operator":         "gt",
        "threshold":        32.0,   # well above any stage ceiling
        "action":           "FAN_ON",
        "device_id":        "esp32-gh-01",
        "pulse_duration_ms": 0,
    },
]


# ── Seed logic ────────────────────────────────────────────────────────────────

async def seed() -> None:
    await init_db()

    async with async_session_maker() as session:
        async with session.begin():
            await _seed_policies(session)
            await _seed_rules(session)

    print("\nAlbion seed complete.")
    print(f"  WateringPolicy rows : {len(POLICIES)}")
    print(f"  ControlRule rows    : {len(RULES)}")


async def _seed_policies(session: AsyncSession) -> None:
    from sqlalchemy import select

    for data in POLICIES:
        existing = (await session.execute(
            select(WateringPolicy).where(WateringPolicy.plant_stage == data["plant_stage"])
        )).scalars().first()

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            print(f"  Updated WateringPolicy: {data['plant_stage'].value}")
        else:
            session.add(WateringPolicy(**data))
            print(f"  Inserted WateringPolicy: {data['plant_stage'].value}")


async def _seed_rules(session: AsyncSession) -> None:
    from sqlalchemy import select

    for data in RULES:
        existing = (await session.execute(
            select(ControlRule).where(ControlRule.name == data["name"])
        )).scalars().first()

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            print(f"  Updated  ControlRule: {data['name']}")
        else:
            session.add(ControlRule(**data))
            print(f"  Inserted ControlRule: {data['name']}")


if __name__ == "__main__":
    asyncio.run(seed())
