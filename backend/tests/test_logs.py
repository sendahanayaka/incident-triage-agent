"""Tests for logs explorer endpoint."""

from fastapi.testclient import TestClient


def test_get_logs_default(client: TestClient) -> None:
    """Verify GET /api/logs retrieves operational logs."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "service_name" in logs[0]
    assert "severity" in logs[0]
    assert "message" in logs[0]


def test_get_logs_filter_by_service(client: TestClient) -> None:
    """Verify GET /api/logs filters by service."""
    response = client.get("/api/logs?service=payments-api")
    assert response.status_code == 200
    logs = response.json()
    assert all(log["service_name"] == "payments-api" for log in logs)


def test_get_logs_filter_by_severity(client: TestClient) -> None:
    """Verify GET /api/logs filters by severity."""
    response = client.get("/api/logs?severity=ERROR")
    assert response.status_code == 200
    logs = response.json()
    assert all(log["severity"] == "ERROR" for log in logs)


def test_get_logs_invalid_severity(client: TestClient) -> None:
    """Verify GET /api/logs rejects invalid severity with 400."""
    response = client.get("/api/logs?severity=CRITICAL_INVALID")
    assert response.status_code == 400
    assert "invalid severity" in response.json()["detail"].lower()


def test_get_logs_empty_result(client: TestClient) -> None:
    """Verify GET /api/logs returns empty list when no matches."""
    response = client.get("/api/logs?service=nonexistent-service")
    assert response.status_code == 200
    assert response.json() == []


def test_get_logs_limit(client: TestClient) -> None:
    """Verify GET /api/logs respects limit parameter."""
    response = client.get("/api/logs?limit=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5
