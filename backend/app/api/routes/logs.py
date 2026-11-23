"""Operational logs endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import get_operational_service
from backend.app.models.log import LogEntryResponse
from backend.app.services.operational_service import OperationalService

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get(
    "",
    response_model=list[LogEntryResponse],
    summary="Query Operational Logs",
    description="Retrieve telemetry logs with optional filtering by service, severity, and limit.",
)
async def get_logs(
    service: str | None = Query(default=None, description="Filter by service name, e.g. payments-api"),
    severity: str | None = Query(default=None, description="Filter by severity: INFO, WARN, ERROR, FATAL"),
    limit: int = Query(default=50, ge=1, le=500, description="Max logs to return (1-500)"),
    operational_service: OperationalService = Depends(get_operational_service),
) -> list[LogEntryResponse]:
    """Retrieve operational logs."""
    try:
        return operational_service.get_logs(service=service, severity=severity, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
