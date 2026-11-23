"""Human-in-the-loop approvals endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.dependencies import get_approval_service
from backend.app.models.approval import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalResponse,
)
from backend.app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get(
    "/pending",
    response_model=list[ApprovalResponse],
    summary="List Pending Approvals",
    description="Retrieve all proposed actions requiring human-in-the-loop approval.",
)
async def get_pending_approvals(
    service: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalResponse]:
    """Return pending approvals without executing them."""
    return service.get_pending()


@router.post(
    "/{id}/approve",
    response_model=ApprovalDecisionResponse,
    summary="Approve Action",
    description="Approve and execute a pending mutating action under safety controls.",
)
async def approve_action(
    id: str,
    decision: ApprovalDecisionRequest | None = None,
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalDecisionResponse:
    """Approve a pending action and execute it."""
    operator = decision.operator if decision else "operator"
    note = decision.note if decision else None
    try:
        return service.approve(id, operator=operator, note=note)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{id}' not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute approved action: {str(exc)}",
        ) from exc


@router.post(
    "/{id}/reject",
    response_model=ApprovalDecisionResponse,
    summary="Reject Action",
    description="Reject a pending action, preventing execution.",
)
async def reject_action(
    id: str,
    decision: ApprovalDecisionRequest | None = None,
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalDecisionResponse:
    """Reject a pending action without executing it."""
    operator = decision.operator if decision else "operator"
    reason = decision.note if decision else None
    try:
        return service.reject(id, operator=operator, reason=reason)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{id}' not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
