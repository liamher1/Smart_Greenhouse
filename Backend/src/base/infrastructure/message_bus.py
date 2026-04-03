"""Async in-process message bus for command and event dispatch.

This component provides two routing modes:
- Commands: one message type -> one handler.
- Events: one message type -> many handlers (fan-out).

It keeps infrastructure concerns centralized while allowing feature handlers
to remain decoupled from transport details.
"""

import asyncio
from typing import Any, Callable, Dict, List, Type
from loguru import logger


class MessageBus:
    """
    Central asynchronous dispatcher for application messages.

    Routing strategy:
    - Command types are mapped to exactly one handler.
    - Event types are mapped to zero or more subscriber handlers.

    Notes:
    - Dispatch uses exact runtime type matching via ``type(message)``.
    - Command errors are re-raised.
    - Event handler errors are logged per handler while other handlers continue.
    """

    def __init__(self):
        # Maps a Command type to a single handler (1:1)
        self._command_handlers: Dict[Type, Callable] = {}
        # Maps an Event type to a list of subscribers (1:N)
        self._event_handlers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, handler: Callable):
        """Register an event subscriber for the given event type.

        Args:
            event_type: Event class used as the routing key.
            handler: Async callable that accepts one event instance.
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        handler_name = getattr(handler, "__name__", type(handler).__name__)
        logger.debug(f"Subscribed {handler_name} to {event_type.__name__}")

    def register_command(self, command_type: Type, handler: Callable):
        """Register the command handler for a command type.

        If the same command type is registered again, the previous handler is
        replaced by the new one.

        Args:
            command_type: Command class used as the routing key.
            handler: Async callable that accepts one command instance.
        """
        self._command_handlers[command_type] = handler
        handler_name = getattr(handler, "__name__", type(handler).__name__)
        logger.debug(f"Registered {handler_name} for {command_type.__name__}")

    async def handle(self, message: Any):
        """Route an incoming message to command or event handlers.

        Args:
            message: Command or event object to dispatch.

        The route is selected using the message's exact runtime type.
        """
        msg_type = type(message)

        if msg_type in self._command_handlers:
            await self._handle_command(message)
        elif msg_type in self._event_handlers:
            await self._handle_event(message)
        else:
            logger.warning(f"No handler found for: {msg_type.__name__}")

    async def _handle_command(self, command: Any):
        """Execute the single registered command handler.

        Args:
            command: Command instance.

        Raises:
            Exception: Re-raises any handler exception after logging.
        """
        handler = self._command_handlers[type(command)]
        try:
            logger.info(f"Executing command: {type(command).__name__}")
            await handler(command)
        except Exception as e:
            logger.error(f"Command {type(command).__name__} failed: {e}")
            raise

    async def _handle_event(self, event: Any):
        """Broadcast an event to all subscribed handlers concurrently.

        Args:
            event: Event instance.

        Uses ``asyncio.gather(..., return_exceptions=True)`` so one failing
        subscriber does not prevent other subscribers from running.
        """
        handlers = self._event_handlers[type(event)]

        tasks = [handler(event) for handler in handlers]
        logger.info(f"Gathering {len(tasks)} handlers for {type(event).__name__}")
        # Collect outcomes from all handlers, including raised exceptions.
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build structured context for logs from pydantic models or plain objects.
        event_context = event.model_dump() if hasattr(event, "model_dump") else getattr(event, "__dict__", str(event))
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                handler_name = getattr(handler, "__name__", type(handler).__name__)
                logger.opt(exception=result).error(
                    "Event handler failed | event_type={} handler={} event_context={}",
                    type(event).__name__,
                    handler_name,
                    event_context,
                )

