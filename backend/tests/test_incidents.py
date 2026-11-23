"""Tests for incidents endpoints."""

import sqlite3
from fastapi.testclient import TestClient
from backend.app.core.config import Settings


def test_get_incidents_empty(client: TestClient) -> None:
    """Verify GET /api/incidents returns empty list when no incidents exist."""
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert response.json() == []


def test_get_incidents_populated(client: TestClient, test_settings: Settings) -> None:
    """Verify GET /api/incidents returns incident tickets from SQLite."""
    db_path = test_settings.resolved_database_path
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incident_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            summary TEXT NOT NULL,
            assignee TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO incident_tickets (created_at, title, severity, summary, assignee)
        VALUES ('2026-11-23T10:00:00Z', 'Payments Gateway Timeout', 'HIGH', 'Timeout lowered in pay-204', 'payments-team')
        """
    )
    conn.commit()
    conn.close()

    response = client.get("/api/incidents")
    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) == 1
    ticket = incidents[0]
    assert ticket["ticket_id"] == "INC-1042"  # 1 + 1041
    assert ticket["title"] == "Payments Gateway Timeout"
    assert ticket["severity"] == "HIGH"
    assert ticket["assignee"] == "payments-team"
