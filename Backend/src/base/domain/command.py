"""
Base Command class for domain-driven design.

This module provides the foundation for all domain commands in the Smart Greenhouse system.
Commands represent an intent to perform an action and are the primary way to modify system state.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar
import uuid


TResult = TypeVar("TResult")


@dataclass(frozen=True)
class Command(ABC, Generic[TResult]):
    """
    Abstract base class for all domain commands.

    Commands represent an explicit intent to perform an action that will modify
    the state of the greenhouse system. Each command is executed by a handler
    and may result in one or more domain events being published.

    Commands should be immutable once created and should only contain data
    necessary to execute the command. Business logic for validation and
    execution should be in command handlers.

    Attributes:
        command_id (uuid.UUID): Unique identifier for each command instance.
        timestamp (datetime): When the command was created (UTC).
    """
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate the command's data integrity and business rules.

        Subclasses must implement this method to perform synchronous validation
        of command parameters. This is called before the command is sent to handlers.

        Returns:
            bool: True if the command is valid, False otherwise.

        Raises:
            ValueError: If validation fails with specific error messages.
        """
        pass


    def __eq__(self, other: Any) -> bool:
        """Compare two commands based on their command_id."""
        if not isinstance(other, Command):
            return False
        return self.command_id == other.command_id

    def __hash__(self) -> int:
        """Generate hash based on command_id for use in collections."""
        return hash(self.command_id)

    def __repr__(self) -> str:
        """Return string representation of the command."""
        return f"{self.__class__.__name__}(command_id={self.command_id}, timestamp={self.timestamp.isoformat()})"
