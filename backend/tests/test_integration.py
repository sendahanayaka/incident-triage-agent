"""Integration tests verifying architectural separation and end-to-end safety workflows."""

from fastapi.testclient import TestClient
from backend.app.approvals.manager import create_approval
from backend.app.core.config import Settings
from backend.app.safety.guardrails import (
    is_safe_action,
    requires_approval,
    validate_action_execution,
)


def test_architectural_separation_rest_and_mcp() -> None:
    """Verify safety guardrail policies distinguish read-only MCP queries from mutations."""
    # Read-only queries must be safe
    assert is_safe_action("telemetry__search_logs")
    assert is_safe_action("telemetry__get_deployment_history")
    assert is_safe_action("filesystem__read_text_file")
    assert not requires_approval("telemetry__search_logs")

    # Mutations must require human-in-the-loop approval
    assert requires_approval("create_incident_ticket")
    assert requires_approval("telemetry__create_incident_ticket")
    assert requires_approval("rollback_deployment")

    allowed, reason = validate_action_execution("telemetry__search_logs", is_approved=False)
    assert allowed

    allowed, reason = validate_action_execution("rollback_deployment", is_approved=False)
    assert not allowed
    assert "requires human approval" in reason


def test_investigation_triggers_approval_lifecycle(
    client: TestClient, test_settings: Settings
) -> None:
    """Verify complete lifecycle: investigation -> pending approval -> human rejection/approval."""
    # 1. Start investigation
    inv_res = client.post(
        "/api/investigations",
        json={"query": "Investigate payments failure and create ticket"},
    )
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["status"] == "completed"

    # 2. Agent proposes an action requiring approval
    appr = create_approval(
        test_settings.resolved_database_path,
        action_type="create_incident_ticket",
        description="Create ticket for payments timeout incident",
        parameters={
            "title": "Payments Outage pay-204",
            "severity": "HIGH",
            "summary": "Gateway timeout dropped to 250ms causing 504 errors.",
            "assignee": "payments-oncall",
        },
        risk_level="HIGH",
    )

    # 3. Retrieve pending approvals via REST API
    pending_res = client.get("/api/approvals/pending")
    assert pending_res.status_code == 200
    assert any(a["id"] == appr.id for a in pending_res.json())

    # 4. Human operator approves the proposed action
    decision_res = client.post(
        f"/api/approvals/{appr.id}/approve",
        json={"operator": "lead-sre", "note": "Root cause verified via telemetry logs."},
    )
    assert decision_res.status_code == 200
    assert decision_res.json()["status"] == "approved"
    assert decision_res.json()["execution_status"] == "executed"

    # 5. Verify the incident was persisted and is queryable through the incidents API
    incidents_res = client.get("/api/incidents")
    assert incidents_res.status_code == 200
    tickets = incidents_res.json()
    assert len(tickets) >= 1
    assert any(t["title"] == "Payments Outage pay-204" for t in tickets)
