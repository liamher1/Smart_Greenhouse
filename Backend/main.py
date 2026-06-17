import asyncio
import sys
from contextlib import asynccontextmanager

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from fastapi import FastAPI
from loguru import logger

from config import config
from base.infrastructure.database import init_db, async_session_maker
from base.infrastructure.message_bus import MessageBus
from base.infrastructure.mqtt_driver import MqttDriver

from features.telemetry.handlers import TelemetryEventHandler
from features.telemetry.events import TelemetryRecorded
from features.telemetry.entrypoints import register_telemetry_entrypoint

from features.actuation.handlers import RuleTriggeredHandler
from features.actuation.service import ActuationService
from features.actuation.listeners import register_actuation_ack_listener
from features.actuation.router import router as actuation_router

from features.automation.events import RuleTriggered
from features.automation.handlers import RipenessHandler, TelemetryAutomationHandler
from features.automation.router import router as automation_router
from features.vision.events import FruitRipenessDetected


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up all infrastructure on startup; tear it down on shutdown."""
    logger.info("Starting the greenhouse backend...")

    # 1. Database
    try:
        await init_db()
        logger.success("Database initialized.")
    except Exception as e:
        logger.error(f"DB init failed: {e}")

    # 2. Message Bus
    message_bus = MessageBus()

    # 3. Telemetry — per-message session boundaries
    telemetry_handler = TelemetryEventHandler(session_factory=async_session_maker)
    message_bus.subscribe(TelemetryRecorded, telemetry_handler)
    logger.info("Telemetry feature wired up.")

    # 4. MQTT driver
    mqtt_driver = MqttDriver(
        broker_url=config.MQTT_BROKER_IP,
        broker_port=config.MQTT_PORT,
        client_id="backend_service",
    )

    # 5. Actuation — attach service to app.state so the router can resolve it
    actuation_service = ActuationService(mqtt_driver)
    register_actuation_ack_listener(mqtt_driver, actuation_service)
    app.state.actuation_service = actuation_service

    rule_triggered_handler = RuleTriggeredHandler(actuation_service)
    message_bus.subscribe(RuleTriggered, rule_triggered_handler)
    logger.info("Actuation feature wired up.")

    # 5b. Automation — policy-aware rule engine + ripeness-driven phase switching
    ripeness_handler = RipenessHandler(async_session_maker, message_bus)
    message_bus.subscribe(FruitRipenessDetected, ripeness_handler)

    telemetry_automation_handler = TelemetryAutomationHandler(async_session_maker, message_bus)
    message_bus.subscribe(TelemetryRecorded, telemetry_automation_handler)
    logger.info("Automation feature wired up.")

    # 6. Register all MQTT topic callbacks before connecting
    register_telemetry_entrypoint(mqtt_driver, message_bus)

    from features.vision.entrypoints import register_vision_entrypoint
    register_vision_entrypoint(mqtt_driver, message_bus)

    # 7. Connect to broker and start the MQTT listener as a background task
    await mqtt_driver.connect()
    logger.success(f"MQTT connected at {config.MQTT_BROKER_IP}:{config.MQTT_PORT}")
    mqtt_task = asyncio.create_task(mqtt_driver.run())

    yield  # HTTP server is live here

    # Shutdown
    mqtt_task.cancel()
    try:
        await mqtt_task
    except asyncio.CancelledError:
        pass
    await mqtt_driver.disconnect()
    logger.info("Backend shutdown complete.")


app = FastAPI(title="Smart Greenhouse API", version="0.1.0", lifespan=lifespan)

app.include_router(actuation_router)
app.include_router(automation_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, loop="none")
