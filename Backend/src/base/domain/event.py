from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
import uuid


@dataclass(frozen=True)
class Event(ABC):
    """
    Abstract base class for domain events.

    Events represent something that has happened in the past within the greenhouse system.
    They are immutable and often broadcasted to multiple handlers for processing.
    Each event is uniquely identified and timestamped for audit trails and event sourcing.
    """
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary representation.

        Must be implemented by subclasses to enable serialization for storage or transmission.

        Returns:
            Dict[str, Any]: Dictionary representation of the event including base fields.
        """
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
        }

    def __eq__(self, other: Any) -> bool:
        """Compare events based on their event_id."""
        if not isinstance(other, Event):
            return False
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        """Generate hash based on event_id for use in collections."""
        return hash(self.event_id)

    def __repr__(self) -> str:
        """Return string representation of the event."""
        return f"{self.__class__.__name__}(event_id={self.event_id}, timestamp={self.timestamp.isoformat()})"
