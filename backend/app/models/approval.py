"""Human-in-the-loop approval workflow models."""

from typing import Any
from pydantic import BaseModel, Field


class ApprovalResponse(BaseModel):
    """Approval request details."""

    id: str = Field(..., description="Unique approval identifier, e.g. app-12345")
    action_type: str = Field(
        ...,
        description="Action type: create_incident_ticket, rollback_deployment, restart_service, etc."
    )
    description: str = Field(..., description="Human-readable description of the proposed action")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters to pass if approved")
    risk_level: str = Field(default="HIGH", description="Risk tier: LOW, MEDIUM, HIGH, CRITICAL")
    status: str = Field(default="pending", description="Status: pending, approved, rejected")
    created_at: str = Field(..., description="UTC ISO timestamp of request")
    requested_by: str = Field(default="agent", description="Requesting entity: agent, user, etc.")
    decision_at: str | None = Field(default=None, description="UTC ISO timestamp of decision")
    decision_by: str | None = Field(default=None, description="Operator who approved or rejected")
    execution_status: str = Field(
        default="pending",
        description="Execution status: pending, executed, failed, skipped"
    )
    execution_result: dict[str, Any] | None = Field(
        default=None, description="Result payload if executed"
    )


class ApprovalsListResponse(BaseModel):
    """List of approval requests."""

    approvals: list[ApprovalResponse] = Field(default_factory=list)
    total: int = Field(default=0)


class ApprovalDecisionRequest(BaseModel):
    """Optional payload when making an approval decision."""

    operator: str = Field(default="operator", description="Name or identifier of the deciding operator")
    note: str | None = Field(default=None, description="Optional explanation or reason")


class ApprovalDecisionResponse(BaseModel):
    """Result of an approval or rejection operation."""

    approval_id: str = Field(..., description="Approval identifier")
    status: str = Field(..., description="New status: approved or rejected")
    action_type: str = Field(..., description="Action type")
    execution_status: str = Field(..., description="Execution status: executed, skipped, or failed")
    execution_result: dict[str, Any] | None = Field(default=None, description="Execution result if any")
    message: str = Field(..., description="Summary of decision and execution outcome")
