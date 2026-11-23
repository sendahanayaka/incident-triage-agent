"""Incident ticket models matching SQLite persistence."""

from pydantic import BaseModel, Field


class IncidentResponse(BaseModel):
    """Persisted incident ticket."""

    ticket_id: str = Field(..., description="Formatted ticket ID, e.g. INC-1042")
    created_at: str = Field(..., description="Creation UTC timestamp")
    title: str = Field(..., description="Incident title")
    severity: str = Field(..., description="Severity level, e.g. HIGH, CRITICAL, MEDIUM, LOW")
    summary: str = Field(..., description="Incident summary and symptoms")
    assignee: str = Field(..., description="Assigned team or individual")


class IncidentsListResponse(BaseModel):
    """List of incident tickets."""

    incidents: list[IncidentResponse] = Field(default_factory=list)
    total: int = Field(default=0)


class CreateIncidentRequest(BaseModel):
    """Payload to create an incident ticket."""

    title: str = Field(..., min_length=1, description="Incident title")
    severity: str = Field(..., min_length=1, description="Severity label")
    summary: str = Field(..., min_length=1, description="Incident summary and evidence")
    assignee: str = Field(..., min_length=1, description="Assignee")
