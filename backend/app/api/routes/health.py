"""Health check endpoint."""

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_settings
from backend.app.core.config import Settings
from backend.app.models.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check",
    description="Check whether the backend service is running and healthy.",
)
async def check_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return backend health status."""
    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        version="1.0.0",
        environment=settings.app_env,
    )
