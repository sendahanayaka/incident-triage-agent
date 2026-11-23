"""Deployments history endpoints."""

from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_operational_service
from backend.app.models.deployment import DeploymentResponse
from backend.app.services.operational_service import OperationalService

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.get(
    "",
    response_model=list[DeploymentResponse],
    summary="List Deployment History",
    description="Retrieve recent deployments and rollback statuses with optional service filter.",
)
async def get_deployments(
    service: str | None = Query(default=None, description="Filter by service name"),
    operational_service: OperationalService = Depends(get_operational_service),
) -> list[DeploymentResponse]:
    """Retrieve deployment history."""
    return operational_service.get_deployments(service=service)
