"""API dependencies for FastAPI route handlers."""

from functools import lru_cache
from fastapi import Depends

from backend.app.core.config import Settings, settings
from backend.app.services.approval_service import ApprovalService
from backend.app.services.incident_service import IncidentService
from backend.app.services.investigation_service import InvestigationService
from backend.app.services.operational_service import OperationalService
from backend.app.services.trace_service import TraceService


@lru_cache
def get_settings() -> Settings:
    """Provide cached application settings."""
    return settings


def get_operational_service(
    app_settings: Settings = Depends(get_settings),
) -> OperationalService:
    """Dependency for OperationalService."""
    return OperationalService(app_settings)


def get_incident_service(
    app_settings: Settings = Depends(get_settings),
) -> IncidentService:
    """Dependency for IncidentService."""
    return IncidentService(app_settings)


def get_approval_service(
    app_settings: Settings = Depends(get_settings),
) -> ApprovalService:
    """Dependency for ApprovalService."""
    return ApprovalService(app_settings)


def get_trace_service(
    app_settings: Settings = Depends(get_settings),
) -> TraceService:
    """Dependency for TraceService."""
    return TraceService(app_settings)


def get_investigation_service(
    app_settings: Settings = Depends(get_settings),
) -> InvestigationService:
    """Dependency for InvestigationService."""
    return InvestigationService(app_settings)
