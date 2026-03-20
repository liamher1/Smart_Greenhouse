"""
Pydantic schemas for validating incoming MQTT messages.

This module defines the strict data contracts for messages received from the
physical devices. Following the Clean Architecture principles, this is the
"gatekeeper" that ensures all data entering the system is well-formed
before it's passed to any business logic.
"""
from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field


class MessageHeader(BaseModel):
    """
    Defines the mandatory header for all incoming messages.

    The header contains metadata essential for routing and auditing.
    """
    type: str = Field(..., description="The type of the message, e.g., 'telemetry'.")
    device_id: str = Field(..., description="The unique identifier of the sending device.")
    timestamp: datetime = Field(..., description="The UTC timestamp when the message was sent.")


class MessageEnvelope(BaseModel):
    """
    The root model for any message received via MQTT.

    An incoming JSON message must have a 'header' and a 'payload'.
    The payload is a flexible dictionary, allowing different features
    to define their own data structures.
    """
    header: MessageHeader
    payload: Dict[str, Any]

