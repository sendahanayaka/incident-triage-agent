"""Log models for operational log querying."""

from enum import Enum
from pydantic import BaseModel, Field


class LogSeverity(str, Enum):
    """Allowed log severities."""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogEntryResponse(BaseModel):
    """Structured operational log entry."""

    id: str = Field(..., description="Log ID, e.g. LOG-037")
    timestamp: str = Field(..., description="UTC ISO 8601 timestamp")
    service_name: str = Field(..., description="Originating service name")
    severity: str = Field(..., description="Log severity level (INFO, WARN, ERROR, FATAL)")
    event: str = Field(..., description="Event name")
    message: str = Field(..., description="Log message text")


class LogsListResponse(BaseModel):
    """List of operational logs with pagination metadata."""

    logs: list[LogEntryResponse] = Field(default_factory=list)
    total: int = Field(default=0)
