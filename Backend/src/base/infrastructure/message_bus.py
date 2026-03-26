import asyncio
from typing import Any, Callable, Dict, List, Type
from loguru import logger


class MessageBus:
    """
    The central communication hub of the application.
    Routes Commands to a single handler and Events to multiple subscribers.
    """

    def __init__(self):
        # Maps a Command type to a single handler (1:1)
        self._command_handlers: Dict[Type, Callable] = {}
        # Maps an Event type to a list of subscribers (1:N)
        self._event_handlers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, handler: Callable):
        """Register a handler to react to a specific event"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        handler_name = getattr(handler, "__name__", handler.__class__.__name__)
        logger.debug(f"Subscribed {handler_name} to {event_type.__name__}")

    def register_command(self, command_type: Type, handler: Callable):
        """Register a handler to execute a specific command"""
        self._command_handlers[command_type] = handler
        handler_name = getattr(handler, "__name__", handler.__class__.__name__)
        logger.debug(f"Registered {handler_name} for {command_type.__name__}")

    async def handle(self, message: Any):
        """Routes the message based on whether it's a Command or an Event"""
        msg_type = type(message)

        if msg_type in self._command_handlers:
            await self._handle_command(message)
        elif msg_type in self._event_handlers:
            await self._handle_event(message)
        else:
            logger.warning(f"No handler found for: {msg_type.__name__}")

    async def _handle_command(self, command: Any):
        """Executes the single registered handler for a command"""
        handler = self._command_handlers[type(command)]
        try:
            logger.info(f"Executing command: {type(command).__name__}")
            await handler(command)
        except Exception as e:
            logger.error(f"Command {type(command).__name__} failed: {e}")
            raise

    async def _handle_event(self, event: Any):
        """Broadcasts an event to all subscribed handlers"""
        handlers = self._event_handlers[type(event)]

        tasks = [handler(event) for handler in handlers]
        logger.info(f"Gathering {len(tasks)} handlers for {type(event).__name__}")
        await asyncio.gather(*tasks, return_exceptions=True)
        #2

