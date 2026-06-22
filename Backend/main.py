import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pathlib import Path

from config import config
from base.infrastructure.database import init_db, async_session_maker
from base.infrastructure.message_bus import MessageBus
from base.infrastructure.mqtt_driver import MqttDriver

from features.telemetry.handlers import TelemetryEventHandler
from features.telemetry.events import TelemetryRecorded
from features.telemetry.entrypoints import register_telemetry_entrypoint
from features.telemetry.router import router as telemetry_router

from features.actuation.handlers import RuleTriggeredHandler
from features.actuation.service import ActuationService
from features.actuation.listeners import register_actuation_ack_listener
from features.actuation.router import router as actuation_router

from features.automation.events import RuleTriggered
from features.automation.handlers import RipenessHandler, TelemetryAutomationHandler
from features.automation.router import router as automation_router
from features.vision.events import FruitRipenessDetected
from features.vision.handlers import VisionReadingHandler
from features.vision.router import router as vision_router


class _WsManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self._connections -= dead


class _TelemetryWSBroadcaster:
    def __init__(self, manager: _WsManager):
        self._mgr = manager

    async def handle(self, event: TelemetryRecorded):
        await self._mgr.broadcast({
            "type": "telemetry",
            "device_id": event.device_id,
            "temperature": event.temperature,
            "humidity": event.humidity,
            "soil_moisture": event.soil_moisture,
            "water_level": event.water_level,
            "timestamp": event.timestamp.isoformat(),
        })


ws_manager = _WsManager()


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
    ws_broadcaster = _TelemetryWSBroadcaster(ws_manager)
    message_bus.subscribe(TelemetryRecorded, ws_broadcaster)
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

    vision_reading_handler = VisionReadingHandler(async_session_maker)
    message_bus.subscribe(FruitRipenessDetected, vision_reading_handler)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router)
app.include_router(actuation_router)
app.include_router(automation_router)
app.include_router(vision_router)

# Serve captured images
images_dir = Path(config.IMAGE_SAVE_DIR)
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

# Serve React frontend build if present
_react_build = Path(__file__).parent.parent / "Frontend" / "dist"
if _react_build.exists():
    app.mount("/", StaticFiles(directory=str(_react_build), html=True), name="frontend")


@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
