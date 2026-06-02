from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RuleTriggered(BaseModel):
    """Published by TelemetryAutomationHandler when a ControlRule threshold is crossed."""

    model_config = ConfigDict(frozen=True)

    rule_id: UUID
    device_id: str
    action: str           # Must be a valid ActuationAction value
    pulse_duration_ms: int
