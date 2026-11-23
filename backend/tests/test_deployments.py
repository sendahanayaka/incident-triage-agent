"""Tests for deployments history endpoint."""

from fastapi.testclient import TestClient


def test_get_deployments_list(client: TestClient) -> None:
    """Verify GET /api/deployments returns deployment history."""
    response = client.get("/api/deployments")
    assert response.status_code == 200
    deployments = response.json()
    assert isinstance(deployments, list)
    assert len(deployments) >= 4

    sample = deployments[0]
    assert "deployment_id" in sample
    assert "service_name" in sample
    assert "version" in sample
    assert "commit_hash" in sample
    assert "rollback_status" in sample


def test_get_deployments_filter_by_service(client: TestClient) -> None:
    """Verify GET /api/deployments filters by service."""
    response = client.get("/api/deployments?service=payments-api")
    assert response.status_code == 200
    deployments = response.json()
    assert all(d["service_name"] == "payments-api" for d in deployments)
    assert len(deployments) >= 2


def test_get_deployments_empty_service(client: TestClient) -> None:
    """Verify GET /api/deployments returns empty list for unknown service."""
    response = client.get("/api/deployments?service=unknown-service")
    assert response.status_code == 200
    assert response.json() == []
