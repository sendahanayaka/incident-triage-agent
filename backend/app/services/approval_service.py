"""Approval service coordinating human-in-the-loop approvals."""

from backend.app.approvals.manager import (
    approve_action,
    create_approval,
    get_approval,
    get_pending_approvals,
    reject_action,
)
from backend.app.core.config import Settings, settings
from backend.app.models.approval import (
    ApprovalDecisionResponse,
    ApprovalResponse,
)


class ApprovalService:
    """Service for managing pending approvals and safety verification."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings

    def get_pending(self) -> list[ApprovalResponse]:
        """List all pending approval actions."""
        return get_pending_approvals(self.settings.resolved_database_path)

    def get_by_id(self, approval_id: str) -> ApprovalResponse | None:
        """Get an approval by ID."""
        return get_approval(self.settings.resolved_database_path, approval_id)

    def approve(
        self,
        approval_id: str,
        operator: str = "operator",
        note: str | None = None,
    ) -> ApprovalDecisionResponse:
        """Approve and execute a pending action."""
        return approve_action(
            self.settings.resolved_database_path,
            approval_id=approval_id,
            operator=operator,
            note=note,
        )

    def reject(
        self,
        approval_id: str,
        operator: str = "operator",
        reason: str | None = None,
    ) -> ApprovalDecisionResponse:
        """Reject a pending action."""
        return reject_action(
            self.settings.resolved_database_path,
            approval_id=approval_id,
            operator=operator,
            reason=reason,
        )
