"""Incident ticket endpoints."""

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_incident_service
from backend.app.models.incident import IncidentResponse
from backend.app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=list[IncidentResponse],
    summary="List Incident Tickets",
    description="Retrieve all persisted incident tickets from the database.",
)
async def list_incidents(
    incident_service: IncidentService = Depends(get_incident_service),
) -> list[IncidentResponse]:
    """Return persisted incident tickets."""
    return incident_service.get_incidents()
