"""Tests for operational services endpoint."""

from fastapi.testclient import TestClient


def test_get_services_list(client: TestClient) -> None:
    """Verify GET /api/services returns operational services from mock data."""
    response = client.get("/api/services")
    assert response.status_code == 200
    services = response.json()
    assert isinstance(services, list)
    assert len(services) >= 3

    service_names = {s["service_name"] for s in services}
    assert "payments-api" in service_names
    assert "auth-service" in service_names
    assert "notification-worker" in service_names

    # Check structure
    sample = services[0]
    assert "service_name" in sample
    assert "status" in sample
    assert "runbook_available" in sample
    assert "total_deployments" in sample
    assert "error_count" in sample
