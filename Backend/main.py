import asyncio
import sys
from loguru import logger

from config import config

from src.base.infrastructure.database import init_db, async_session_maker
from src.base.infrastructure.message_bus import MessageBus
from src.base.infrastructure.mqtt_driver import MqttDriver

from src.features.telemetry.handlers import TelemetryEventHandler
from src.features.telemetry.events import TelemetryRecorded
from src.features.telemetry.entrypoints import register_telemetry_entrypoint

async def start_app():
    """
    Start the Smart Greenhouse backend application.
    """
    logger.info("Starting the greenhouse backend...")

    # 1. Initialize Database
    try:
        await init_db()
        logger.success("Database initialized and synced!")
    except Exception as e:
        logger.error(f"DB Init Failed: {e}")
        # Continue with other services if DB fails (e.g. MQTT still needs to run)
        # return

    # 2. Initialize Message Bus
    message_bus = MessageBus()
    logger.info("Message Bus initialized.")

    # 3. Setup Telemetry Feature with per-message session boundaries.
    telemetry_handler = TelemetryEventHandler(session_factory=async_session_maker)
    message_bus.subscribe(TelemetryRecorded, telemetry_handler)
    logger.info("Telemetry feature wired up.")

    # 4. Setup MQTT Infrastructure
    mqtt_broker = config.MQTT_BROKER_IP
    mqtt_port = config.MQTT_PORT
    mqtt_client_id = "backend_service"
    
    mqtt_driver = MqttDriver(
        broker_url=mqtt_broker, 
        broker_port=mqtt_port,
        client_id=mqtt_client_id
    )

    # 6. Register Entrypoints (Callback -> Adapter)
    
    register_telemetry_entrypoint(mqtt_driver, message_bus)

    # 6. Start the Application Loop
    try:
        await mqtt_driver.connect()
        logger.success(f"Connected to MQTT Broker at {mqtt_broker}:{mqtt_port}")
        
        # This will block and listen for messages
        await mqtt_driver.run()
    except KeyboardInterrupt:
        logger.info("Stopping backend...")
    except Exception as e:
        logger.error(f"MQTT runtime failed: {e}")
    finally:
        await mqtt_driver.disconnect()
        logger.success("Backend shutdown complete.")

       


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        pass
