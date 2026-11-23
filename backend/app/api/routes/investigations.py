"""Investigation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.dependencies import get_investigation_service
from backend.app.models.investigation import (
    InvestigationDetail,
    InvestigationRequest,
    InvestigationResponse,
)
from backend.app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Incident Investigation",
    description="Initiate an AI-powered investigation for incident triage or release readiness.",
)
async def start_investigation(
    request: InvestigationRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    """Start an investigation using the agent orchestrator."""
    try:
        return await service.start_investigation(request.query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation execution failed: {str(exc)}",
        ) from exc


@router.get(
    "/{id}",
    response_model=InvestigationDetail,
    summary="Retrieve Investigation Details",
    description="Retrieve findings, evidence, tool calls, and status for a specific investigation.",
)
async def get_investigation(
    id: str,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationDetail:
    """Retrieve details for an existing investigation."""
    investigation = service.get_investigation(id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{id}' was not found.",
        )
    return investigation
