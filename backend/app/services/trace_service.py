"""Trace service reading JSONL execution logs."""

from backend.app.core.config import Settings, settings
from backend.app.models.trace import TraceResponse
from backend.app.tracing.tracer import read_traces


class TraceService:
    """Service for retrieving sanitized agent traces."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings

    def get_traces(self, investigation_id: str | None = None) -> list[TraceResponse]:
        """Retrieve traces, optionally filtered by investigation/run ID."""
        return read_traces(self.settings.resolved_trace_file_path, run_id=investigation_id)
