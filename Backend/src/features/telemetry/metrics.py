"""
Telemetry metrics counters for observability.

Provides simple in-memory counters for each processing stage of an
incoming MQTT telemetry message. Counters can be read at any time to
report the current state of the pipeline.
"""
from dataclasses import dataclass, field


@dataclass
class TelemetryMetrics:
    """
    In-memory counters for telemetry message processing stages.

    Attributes:
        received: Total number of MQTT messages received.
        bad_input: Messages rejected due to JSON/schema validation errors.
        failed_persistence: Messages that passed validation but could not be
            persisted to the database.
        successful: Messages fully processed and persisted successfully.
    """

    received: int = field(default=0)
    bad_input: int = field(default=0)
    failed_persistence: int = field(default=0)
    successful: int = field(default=0)

    def increment_received(self) -> None:
        self.received += 1

    def increment_bad_input(self) -> None:
        self.bad_input += 1

    def increment_failed_persistence(self) -> None:
        self.failed_persistence += 1

    def increment_successful(self) -> None:
        self.successful += 1

    def as_dict(self) -> dict:
        """Return all counters as a plain dictionary."""
        return {
            "received": self.received,
            "bad_input": self.bad_input,
            "failed_persistence": self.failed_persistence,
            "successful": self.successful,
        }
