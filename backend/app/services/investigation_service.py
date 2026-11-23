"""Investigation orchestration service."""

import json
import sqlite3
from typing import Any

from backend.app.core.config import Settings, settings
from backend.app.models.investigation import (
    InvestigationDetail,
    InvestigationResponse,
    ToolCallRecord,
)
from backend.app.orchestrator.agent import execute_investigation


class InvestigationService:
    """Service for running and storing incident triage investigations."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure the investigations table exists in SQLite."""
        db_path = self.settings.resolved_database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    status TEXT NOT NULL,
                    findings TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    tool_calls TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    error_message TEXT
                );
                """
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    async def start_investigation(self, query: str) -> InvestigationResponse:
        """Execute a new investigation and persist the results."""
        response = await execute_investigation(query, self.settings)

        # Persist to SQLite
        db_path = self.settings.resolved_database_path
        try:
            conn = sqlite3.connect(str(db_path))
            tool_calls_json = json.dumps([t.model_dump() for t in response.tool_calls])
            conn.execute(
                """
                INSERT OR REPLACE INTO investigations (
                    id, query, status, findings, evidence, recommendations,
                    tool_calls, created_at, completed_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response.id,
                    response.query,
                    response.status,
                    response.findings,
                    json.dumps(response.evidence),
                    json.dumps(response.recommendations),
                    tool_calls_json,
                    response.created_at,
                    response.completed_at,
                    None if response.status == "completed" else response.findings,
                ),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

        return response

    def get_investigation(self, investigation_id: str) -> InvestigationDetail | None:
        """Retrieve an investigation by ID."""
        db_path = self.settings.resolved_database_path
        if not db_path.is_file():
            return None

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, query, status, findings, evidence, recommendations,
                       tool_calls, created_at, completed_at, error_message
                FROM investigations
                WHERE id = ?
                """,
                (investigation_id,),
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            evidence = json.loads(row["evidence"]) if row["evidence"] else []
            recommendations = json.loads(row["recommendations"]) if row["recommendations"] else []
            tool_calls_raw = json.loads(row["tool_calls"]) if row["tool_calls"] else []
            tool_calls = [
                ToolCallRecord(
                    tool=t.get("tool", "unknown"),
                    arguments=t.get("arguments", {}),
                    status=t.get("status", "ok"),
                    duration_ms=t.get("duration_ms"),
                )
                for t in tool_calls_raw
            ]

            return InvestigationDetail(
                id=row["id"],
                query=row["query"],
                status=row["status"],
                findings=row["findings"],
                evidence=evidence,
                recommendations=recommendations,
                tool_calls=tool_calls,
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                error_message=row["error_message"],
            )
        except sqlite3.Error:
            return None
