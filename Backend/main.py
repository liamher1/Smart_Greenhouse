import asyncio
import os
from loguru import logger
from dotenv import load_dotenv

from src.base.infrastructure.database import init_db, async_session_maker
from src.base.infrastructure.message_bus import MessageBus
from src.base.infrastructure.mqtt_adapter import MQTTAdapter

from src.features.telemetry.repository import TelemetryRepository
from src.features.telemetry.handlers import TelemetryEventHandler
from src.features.telemetry.events import TelemetryUpdatedEvent
from src.features.telemetry.entrypoints import TelemetryEntrypoint
from src.features.control.entrypoints import register_control_entrypoints
from src.features.control.handlers import ControlEventHandler
from src.features.control.events import CommandAcknowledgedEvent

load_dotenv()



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

    # 3. Setup Telemetry Feature (Repo -> Handler -> Subs)
    # Note: Using a single session for simplicity. In production, use session per request.
    session = async_session_maker()
    telemetry_repo = TelemetryRepository(session)
    telemetry_handler = TelemetryEventHandler(telemetry_repository=telemetry_repo)
    message_bus.subscribe(TelemetryUpdatedEvent, telemetry_handler)
    logger.info("Telemetry feature wired up.")

    # 4. Setup Control Feature (Handler -> Subs)
    control_handler = ControlEventHandler()
    message_bus.subscribe(CommandAcknowledgedEvent, control_handler)
    logger.info("Control feature wired up.")

    # 5. Setup MQTT Infrastructure
    mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "backend_service")
    
    adapter = MQTTAdapter(
        broker_url=mqtt_broker, 
        broker_port=mqtt_port,
        client_id=mqtt_client_id
    )

    # 6. Register Entrypoints (Callback -> Adapter)
    
    # Telemetry Entrypoint
    telemetry_entrypoint = TelemetryEntrypoint(message_bus)
    # Use the decorator-style registration manually
    adapter.on_message("greenhouse/telemetry/+")(telemetry_entrypoint.handle_reading)
    logger.info("Registered TelemetryEntrypoint on greenhouse/telemetry/+")

    # Control Entrypoint (ACKs)
    register_control_entrypoints(adapter, message_bus)
    
    # 7. Start the Application Loop
    try:
        await adapter.connect()
        logger.success(f"Connected to MQTT Broker at {mqtt_broker}:{mqtt_port}")
        
        # This will block and listen for messages
        await adapter.run()
    except KeyboardInterrupt:
        logger.info("Stopping backend...")
    finally:
        await adapter.disconnect()
        await session.close()
        logger.success("Backend shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        pass
