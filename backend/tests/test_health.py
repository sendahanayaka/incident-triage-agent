"""Tests for health endpoint."""

from fastapi.testclient import TestClient


def test_health_returns_valid_response(client: TestClient) -> None:
    """Verify GET /api/health returns 200 and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["application"] == "IncidentTriageAgentTest"
    assert "version" in data
    assert "environment" in data


def test_root_endpoint_metadata(client: TestClient) -> None:
    """Verify GET / returns navigation metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "IncidentTriageAgentTest"
    assert data["health"] == "/api/health"
