import asyncio
import sys
from loguru import logger

from config import config

from src.base.infrastructure.mqtt_driver import MqttDriver
from src.bootstrap import bootstrap_app

async def start_app():
    """
    Start the Smart Greenhouse backend application.
    """
    logger.info("Starting the greenhouse backend...")

    # 1. Bootstrap App
    app = await bootstrap_app()
    telemetry_controller = app["controller"]
    db_connection = app["db_connection"]
    logger.info("Telemetry feature wired up.")

    # 4. Setup MQTT Infrastructure
    mqtt_broker = config.MQTT_BROKER_IP
    mqtt_port = config.MQTT_PORT
    mqtt_client_id = "backend_service"
    
    adapter = MqttDriver(
        broker_url=mqtt_broker, 
        broker_port=mqtt_port,
        client_id=mqtt_client_id
    )

    # 6. Register Entrypoints (Callback -> Adapter)
    
    # Telemetry Entrypoint
    # Use the decorator-style registration manually
    adapter.on_message("greenhouse/telemetry/+")(telemetry_controller.handle_reading)
    logger.info("Registered TelemetryController on greenhouse/telemetry/+")

    # 6. Start the Application Loop
    try:
        await adapter.connect()
        logger.success(f"Connected to MQTT Broker at {mqtt_broker}:{mqtt_port}")
        
        # This will block and listen for messages
        await adapter.run()
    except KeyboardInterrupt:
        logger.info("Stopping backend...")
    except Exception as e:
        logger.error(f"MQTT runtime failed: {e}")
    finally:
        await adapter.disconnect()
        await db_connection.close()
        logger.success("Backend shutdown complete.")

       


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        pass
