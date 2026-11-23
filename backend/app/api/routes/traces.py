"""Agent traces endpoints."""

from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_trace_service
from backend.app.models.trace import TraceResponse
from backend.app.services.trace_service import TraceService

router = APIRouter(prefix="/traces", tags=["Traces"])


@router.get(
    "",
    response_model=list[TraceResponse],
    summary="Retrieve Agent Traces",
    description="Retrieve execution traces for agent investigations, scrubbed of secrets.",
)
async def get_traces(
    investigation_id: str | None = Query(default=None, description="Filter traces by investigation / run ID"),
    run_id: str | None = Query(default=None, description="Alias for investigation ID"),
    trace_service: TraceService = Depends(get_trace_service),
) -> list[TraceResponse]:
    """Return sanitized agent traces."""
    target_id = investigation_id or run_id
    return trace_service.get_traces(investigation_id=target_id)
