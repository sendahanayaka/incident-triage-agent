"""Health check and configuration status endpoints."""

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_settings
from backend.app.core.config import Settings
from backend.app.models.health import HealthResponse, LLMConfigStatus

DEFAULT_OFFLINE_MODEL = "offline/incident-triage-v1"

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check",
    description="Check whether the backend service is running and healthy.",
)
async def check_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return backend health status with safe LLM provider metadata."""
    effective_model = settings.llm_model if settings.llm_model else (
        DEFAULT_OFFLINE_MODEL if settings.is_offline_mode else "(not configured)"
    )
    llm_status = LLMConfigStatus(
        provider=settings.llm_provider,
        mode=settings.llm_mode,
        model=effective_model,
        has_api_key=settings.has_llm_api_key,
        base_url=settings.llm_base_url,
        is_ready=(settings.is_offline_mode or (settings.has_llm_api_key and bool(settings.llm_model))),
    )
    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        version="1.0.0",
        environment=settings.app_env,
        llm=llm_status,
    )


@router.get(
    "/config/llm",
    response_model=LLMConfigStatus,
    summary="LLM Provider Configuration Status",
    description="Retrieve safe, non-sensitive metadata about the active LLM provider, mode, and model.",
)
async def get_llm_config_status(settings: Settings = Depends(get_settings)) -> LLMConfigStatus:
    """Return current LLM provider and mode status without exposing credentials."""
    effective_model = settings.llm_model if settings.llm_model else (
        DEFAULT_OFFLINE_MODEL if settings.is_offline_mode else "(not configured)"
    )
    return LLMConfigStatus(
        provider=settings.llm_provider,
        mode=settings.llm_mode,
        model=effective_model,
        has_api_key=settings.has_llm_api_key,
        base_url=settings.llm_base_url,
        is_ready=(settings.is_offline_mode or (settings.has_llm_api_key and bool(settings.llm_model))),
    )
