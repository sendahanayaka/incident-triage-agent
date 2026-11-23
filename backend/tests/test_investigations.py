"""Tests for investigations endpoints."""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def test_start_investigation_valid(client: TestClient) -> None:
    """Verify POST /api/investigations starts an investigation."""
    response = client.post(
        "/api/investigations",
        json={"query": "Investigate payments-api errors and timeouts"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"].startswith("inv-")
    assert data["status"] == "completed"
    assert "payments" in data["findings"].lower()
    assert len(data["evidence"]) > 0
    assert len(data["tool_calls"]) > 0


def test_start_investigation_validation_error(client: TestClient) -> None:
    """Verify POST /api/investigations validates minimum query length."""
    response = client.post("/api/investigations", json={"query": "hi"})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_retrieve_investigation_existing(client: TestClient) -> None:
    """Verify GET /api/investigations/{id} retrieves previously stored investigation."""
    post_res = client.post(
        "/api/investigations",
        json={"query": "Investigate auth-service token validation failures"},
    )
    inv_id = post_res.json()["id"]

    get_res = client.get(f"/api/investigations/{inv_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == inv_id
    assert "auth" in data["findings"].lower()
    assert data["status"] == "completed"


def test_retrieve_investigation_not_found(client: TestClient) -> None:
    """Verify GET /api/investigations/{id} returns 404 for unknown ID."""
    response = client.get("/api/investigations/inv-nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_investigation_failure_handling(client: TestClient) -> None:
    """Verify graceful handling when orchestrator fails."""
    with patch(
        "backend.app.services.investigation_service.execute_investigation",
        side_effect=RuntimeError("Simulated LLM connection timeout"),
    ):
        response = client.post(
            "/api/investigations",
            json={"query": "Check payments error rates"},
        )
        assert response.status_code == 500
        assert "investigation execution failed" in response.json()["detail"].lower()
