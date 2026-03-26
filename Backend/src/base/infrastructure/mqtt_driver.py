"""
Generic MQTT Driver for the infrastructure layer.

This adapter handles the low-level details of connecting to an MQTT broker
and subscribing to topics. It uses a decorator-based approach for registering
callbacks, ensuring that the infrastructure layer does not depend on any
feature-specific code.
"""
import asyncio
import json
import uuid
from typing import Callable, Dict, List, Any, Union, Optional
import aiomqtt
from loguru import logger


class MqttDriver:
    """
    Manages MQTT connection and message routing.
    """

    def __init__(self, broker_url: str, broker_port: int, client_id: str = "backend"):
        self.broker_url = broker_url
        self.broker_port = broker_port
        self.client_id = client_id
        self._client_cm = None
        self._client = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}

    def on_message(self, topic: str) -> Callable:
        """
        A decorator to register a callback for a specific MQTT topic.
        """
        def decorator(func: Callable) -> Callable:
            if topic not in self._callbacks:
                self._callbacks[topic] = []
            self._callbacks[topic].append(func)
            logger.debug(f"Registered {func.__name__} for topic '{topic}'")
            return func
        return decorator

    async def connect(self):
        """
        Connects to the MQTT broker.
        """
        if self._client is not None:
            return

        logger.info(f"Connecting to MQTT broker at {self.broker_url}:{self.broker_port}...")
        self._client_cm = aiomqtt.Client(
            hostname=self.broker_url,
            port=self.broker_port,
            identifier=self.client_id,
        )
        self._client = await self._client_cm.__aenter__()
        logger.success("MQTT Driver connected.")

    async def disconnect(self):
        """
        Disconnects from the MQTT broker.
        """
        if self._client_cm:
            await self._client_cm.__aexit__(None, None, None)
            self._client_cm = None
            self._client = None
            logger.info("MQTT Driver disconnected.")

    async def publish(self, topic: str, payload: Union[Dict, str, bytes], qos: int = 0) -> bool:
        """
        Publishes a message to the MQTT broker.

        Args:
            topic (str): The target topic.
            payload (Union[Dict, str, bytes]): The data to send.
            qos (int): Quality of Service level (0, 1, or 2).

        Returns:
            bool: True if published successfully, False otherwise.
        """
        if not self._client:
            logger.error("Cannot publish: MQTT client is not connected.")
            return False

        try:
            if isinstance(payload, dict):
                payload_data = json.dumps(payload)
            elif isinstance(payload, str):
                payload_data = payload
            else:
                payload_data = payload

            logger.debug(f"Publishing to {topic} with QoS {qos}: {payload_data}")
            await self._client.publish(topic, payload=payload_data, qos=qos)
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False


    async def publish_with_device_ack(self, topic: str, payload: Dict[str, Any], timeout: float = 5.0) -> bool:
        """
        Publishes a command and waits for an application-level acknowledgment from the device.

        Args:
            topic (str): The value to publish to.
            payload (Dict): The command payload.
            timeout (float): Time in seconds to wait for the device to respond.

        Returns:
            bool: True if the device acknowledged within the timeout, False otherwise.
        """
        # Generate a unique command ID if not already present
        command_id = payload.get("command_id")
        if not command_id:
            command_id = str(uuid.uuid4())
            payload["command_id"] = command_id

        # Create a future to wait for the response
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_responses[command_id] = future

        try:
            # Publish the command
            success = await self.publish(topic, payload, qos=1)
            if not success:
                logger.error(f"Failed to publish command {command_id} to broker.")
                return False

            # Wait for the device to ACK
            logger.debug(f"Waiting for device ACK for command {command_id} (timeout={timeout}s)...")
            await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"Command {command_id} acknowledged by device.")
            return True

        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for device ACK for command {command_id}.")
            return False
        except Exception as e:
            logger.error(f"Error checking device ACK for {command_id}: {e}")
            return False
        finally:
            # Cleanup
            self._pending_responses.pop(command_id, None)

    def resolve_ack(self, command_id: str) -> bool:
        """
        Resolves a pending command acknowledgment.

        Args:
            command_id (str): The ID of the command to acknowledge.

        Returns:
            bool: True if a pending request was found and resolved, False otherwise.
        """
        if command_id in self._pending_responses:
            future = self._pending_responses[command_id]
            if not future.done():
                future.set_result(True)
                return True
        return False

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """
        Check if a topic matches a subscription pattern with wildcards.
        Supports '+' (single level) and '#' (multi-level at end).
        """
        if pattern == topic:
            return True

        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')

        if '#' in pattern_parts:
            # '#' must be the last part
            if pattern_parts.index('#') != len(pattern_parts) - 1:
                return False  # Invalid pattern
            
            # Check parts before '#'
            prefix_len = len(pattern_parts) - 1
            if len(topic_parts) < prefix_len:
                return False
                
            for i in range(prefix_len):
                if pattern_parts[i] != '+' and pattern_parts[i] != topic_parts[i]:
                    return False
            return True
            
        # No '#', lengths must match
        if len(pattern_parts) != len(topic_parts):
            return False

        for p, t in zip(pattern_parts, topic_parts):
            if p != '+' and p != t:
                return False

        return True

    async def run(self):
        """
        Connects, subscribes to topics, and starts listening for messages.
        """
        if not self._client:
            await self.connect()

        for topic in self._callbacks.keys():
            # MQTT subscribe needs the pattern (e.g., "telemetry/+")
            await self._client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")

        logger.info("MQTT Driver is running and listening for messages...")
        async for message in self._client.messages:
            topic = message.topic.value
            logger.debug(f"Received message on topic: {topic}")

            # Iterate over all registered patterns to find matches
            for pattern, callbacks in self._callbacks.items():
                if self._topic_matches(pattern, topic):
                    for callback in callbacks:
                        # Fire and forget
                        asyncio.create_task(callback(topic, message.payload))

