"""Operational services endpoints."""

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_operational_service
from backend.app.models.service import ServiceResponse
from backend.app.services.operational_service import OperationalService

router = APIRouter(prefix="/services", tags=["Services"])


@router.get(
    "",
    response_model=list[ServiceResponse],
    summary="List Operational Services",
    description="Retrieve simulated operational microservices, their deployment baselines, and health statuses.",
)
async def list_services(
    service: OperationalService = Depends(get_operational_service),
) -> list[ServiceResponse]:
    """Return all operational services."""
    return service.get_services()
