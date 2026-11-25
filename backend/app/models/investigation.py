"""Investigation request and response models."""

from typing import Any
from pydantic import BaseModel, Field

from backend.app.models.approval import ApprovalResponse


class InvestigationRequest(BaseModel):
    """Request payload to initiate an incident or release investigation."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The investigation query, incident symptom, or release readiness question.",
        examples=["Investigate the payments-api and identify the cause of recent errors."],
    )


class ToolCallRecord(BaseModel):
    """Record of a tool call executed during an investigation."""

    tool: str = Field(..., description="Tool name executed")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments provided to tool")
    status: str = Field(default="ok", description="Status of the tool execution")
    duration_ms: float | None = Field(default=None, description="Execution duration in milliseconds")


class InvestigationResponse(BaseModel):
    """Investigation result and summary."""

    id: str = Field(..., description="Unique investigation identifier")
    query: str = Field(..., description="User query submitted")
    status: str = Field(default="completed", description="Investigation status (completed, failed, in_progress)")
    findings: str = Field(..., description="Synthesized investigation findings and root cause analysis")
    evidence: list[str] = Field(default_factory=list, description="Citations of logs, deployments, runbooks")
    recommendations: list[str] = Field(default_factory=list, description="Recommended remediation or action steps")
    tool_calls: list[ToolCallRecord] = Field(default_factory=list, description="List of tools invoked")
    pending_approval: ApprovalResponse | None = Field(
        default=None,
        description="Pending approval record if a mutation action was proposed in this investigation",
    )
    created_at: str = Field(..., description="UTC ISO timestamp of start")
    completed_at: str | None = Field(default=None, description="UTC ISO timestamp of completion")


class InvestigationDetail(InvestigationResponse):
    """Detailed view of an investigation including error details if failed."""

    error_message: str | None = Field(default=None, description="Error message if investigation failed")
