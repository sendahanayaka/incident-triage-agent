"""Tests for approvals workflow endpoints."""

from fastapi.testclient import TestClient
from backend.app.approvals.manager import create_approval
from backend.app.core.config import Settings


def test_get_pending_approvals_empty(client: TestClient) -> None:
    """Verify GET /api/approvals/pending returns empty list when none exist."""
    response = client.get("/api/approvals/pending")
    assert response.status_code == 200
    assert response.json() == []


def test_approve_pending_action(client: TestClient, test_settings: Settings) -> None:
    """Verify approving a pending action executes it and records approval decision."""
    appr = create_approval(
        test_settings.resolved_database_path,
        action_type="create_incident_ticket",
        description="Create ticket for payments timeout",
        parameters={
            "title": "Payment API Failure",
            "severity": "CRITICAL",
            "summary": "Timeout lowered in pay-204",
            "assignee": "payments-sre",
        },
        risk_level="HIGH",
    )

    # Verify pending
    pending_res = client.get("/api/approvals/pending")
    assert pending_res.status_code == 200
    assert len(pending_res.json()) == 1

    # Approve
    approve_res = client.post(
        f"/api/approvals/{appr.id}/approve",
        json={"operator": "sre-lead", "note": "Approved after reviewing runbook"},
    )
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["status"] == "approved"
    assert data["execution_status"] == "executed"
    assert "ticket_id" in data["execution_result"]
    assert data["execution_result"]["ticket_id"].startswith("INC-")

    # Verify no longer in pending
    pending_after = client.get("/api/approvals/pending")
    assert pending_after.json() == []

    # Verify incident was created in database
    incidents_res = client.get("/api/incidents")
    assert len(incidents_res.json()) == 1
    assert incidents_res.json()[0]["title"] == "Payment API Failure"


def test_reject_pending_action(client: TestClient, test_settings: Settings) -> None:
    """Verify rejecting a pending action skips execution and marks rejected."""
    appr = create_approval(
        test_settings.resolved_database_path,
        action_type="rollback_deployment",
        description="Roll back payments-api deployment",
        parameters={"service_name": "payments-api", "target_version": "2.4.1"},
        risk_level="HIGH",
    )

    # Reject
    reject_res = client.post(
        f"/api/approvals/{appr.id}/reject",
        json={"operator": "oncall-lead", "note": "Root cause not yet confirmed"},
    )
    assert reject_res.status_code == 200
    data = reject_res.json()
    assert data["status"] == "rejected"
    assert data["execution_status"] == "skipped"

    # Verify no longer pending
    pending_after = client.get("/api/approvals/pending")
    assert pending_after.json() == []

    # Verify no incident was created
    incidents_res = client.get("/api/incidents")
    assert len(incidents_res.json()) == 0


def test_duplicate_approval_conflict(client: TestClient, test_settings: Settings) -> None:
    """Verify approving an already approved or rejected action returns 409 conflict."""
    appr = create_approval(
        test_settings.resolved_database_path,
        action_type="restart_service",
        description="Restart auth service",
        parameters={"service_name": "auth-service"},
    )

    # First approve
    res1 = client.post(f"/api/approvals/{appr.id}/approve")
    assert res1.status_code == 200

    # Second approve should fail with 409
    res2 = client.post(f"/api/approvals/{appr.id}/approve")
    assert res2.status_code == 409
    assert "already approved" in res2.json()["detail"].lower()


def test_unknown_approval_returns_404(client: TestClient) -> None:
    """Verify approval/rejection of non-existent ID returns 404."""
    res1 = client.post("/api/approvals/app-unknown/approve")
    assert res1.status_code == 404
    res2 = client.post("/api/approvals/app-unknown/reject")
    assert res2.status_code == 404
