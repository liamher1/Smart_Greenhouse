"""FastAPI transport adapter for the actuation feature slice.

The router accepts a user request, turns it into a domain command, and sends
it to the application service. The route returns success only when the device
ACK is received through the MQTT request-reply loop.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from .models import ActuationAction, ActuationCommand
from .service import ActuationService

router = APIRouter(prefix="/api/v1/actuation", tags=["actuation"])


def get_actuation_service(request: Request) -> ActuationService:
    """Resolve ActuationService from FastAPI app state.

    The service is expected to be attached to `app.state.actuation_service`
    during application startup.
    """
    service = getattr(request.app.state, "actuation_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Actuation service is not configured",
        )
    return service


@router.post("/{device_id}/command", status_code=status.HTTP_200_OK)
async def send_actuation_command(
    device_id: str,
    action: ActuationAction = Body(...),
    parameters: dict[str, Any] | None = Body(default=None),
    service: ActuationService = Depends(get_actuation_service),
) -> dict[str, Any]:
    """Create and publish an actuation command for a target device.

    The request body supplies the action and optional parameters while the
    device ID is taken from the path. On success the endpoint returns the
    accepted command metadata; otherwise it raises a 504 timeout error.
    """
    command = ActuationCommand(device_id=device_id, action=action, parameters=parameters)
    is_acked = await service.publish_with_device_ack(command)

    if not is_acked:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out waiting for device ACK",
        )

    return {
        "status": "accepted",
        "command_id": str(command.command_id),
        "device_id": command.device_id,
        "action": command.action,
        "timestamp": command.timestamp,
    }



