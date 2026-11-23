"""Incident ticket service querying SQLite."""

import sqlite3
from backend.app.core.config import Settings, settings
from backend.app.models.incident import IncidentResponse


class IncidentService:
    """Service for accessing incident tickets stored in SQLite."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings

    def get_incidents(self) -> list[IncidentResponse]:
        """Retrieve all incident tickets from the SQLite database."""
        db_path = self.settings.resolved_database_path
        if not db_path.is_file():
            return []

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            # Verify table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='incident_tickets'"
            )
            if not cursor.fetchone():
                conn.close()
                return []

            cursor = conn.execute(
                """
                SELECT id, created_at, title, severity, summary, assignee
                FROM incident_tickets
                ORDER BY id DESC
                """
            )
            rows = cursor.fetchall()
            conn.close()

            incidents: list[IncidentResponse] = []
            for row in rows:
                ticket_id = f"INC-{row['id'] + 1041}"
                incidents.append(
                    IncidentResponse(
                        ticket_id=ticket_id,
                        created_at=row["created_at"],
                        title=row["title"],
                        severity=row["severity"],
                        summary=row["summary"],
                        assignee=row["assignee"],
                    )
                )
            return incidents
        except sqlite3.Error:
            return []
