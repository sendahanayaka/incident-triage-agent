"""Approval workflow manager with SQLite persistence and safety gating."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.models.approval import (
    ApprovalDecisionResponse,
    ApprovalResponse,
)


def _init_db(conn: sqlite3.Connection) -> None:
    """Ensure database tables exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incident_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            summary TEXT NOT NULL,
            assignee TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            parameters TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            decision_at TEXT,
            decision_by TEXT,
            execution_status TEXT NOT NULL,
            execution_result TEXT
        );
        """
    )
    conn.commit()


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection and initialize schema if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def create_approval(
    db_path: Path,
    action_type: str,
    description: str,
    parameters: dict[str, Any],
    risk_level: str = "HIGH",
    requested_by: str = "agent",
) -> ApprovalResponse:
    """Create a new pending approval record."""
    approval_id = f"app-{uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    params_json = json.dumps(parameters)

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO approvals (
                id, action_type, description, parameters, risk_level,
                status, created_at, requested_by, execution_status
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, 'pending')
            """,
            (approval_id, action_type, description, params_json, risk_level, created_at, requested_by),
        )
        conn.commit()
    finally:
        conn.close()

    return ApprovalResponse(
        id=approval_id,
        action_type=action_type,
        description=description,
        parameters=parameters,
        risk_level=risk_level,
        status="pending",
        created_at=created_at,
        requested_by=requested_by,
        execution_status="pending",
    )


def get_pending_approvals(db_path: Path) -> list[ApprovalResponse]:
    """Retrieve all approvals in pending state."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, action_type, description, parameters, risk_level,
                   status, created_at, requested_by, decision_at, decision_by,
                   execution_status, execution_result
            FROM approvals
            WHERE status = 'pending'
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    approvals = []
    for row in rows:
        params = json.loads(row["parameters"]) if row["parameters"] else {}
        exec_res = json.loads(row["execution_result"]) if row["execution_result"] else None
        approvals.append(
            ApprovalResponse(
                id=row["id"],
                action_type=row["action_type"],
                description=row["description"],
                parameters=params,
                risk_level=row["risk_level"],
                status=row["status"],
                created_at=row["created_at"],
                requested_by=row["requested_by"],
                decision_at=row["decision_at"],
                decision_by=row["decision_by"],
                execution_status=row["execution_status"],
                execution_result=exec_res,
            )
        )
    return approvals


def get_approval(db_path: Path, approval_id: str) -> ApprovalResponse | None:
    """Retrieve a single approval by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, action_type, description, parameters, risk_level,
                   status, created_at, requested_by, decision_at, decision_by,
                   execution_status, execution_result
            FROM approvals
            WHERE id = ?
            """,
            (approval_id,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    params = json.loads(row["parameters"]) if row["parameters"] else {}
    exec_res = json.loads(row["execution_result"]) if row["execution_result"] else None
    return ApprovalResponse(
        id=row["id"],
        action_type=row["action_type"],
        description=row["description"],
        parameters=params,
        risk_level=row["risk_level"],
        status=row["status"],
        created_at=row["created_at"],
        requested_by=row["requested_by"],
        decision_at=row["decision_at"],
        decision_by=row["decision_by"],
        execution_status=row["execution_status"],
        execution_result=exec_res,
    )


def approve_action(
    db_path: Path,
    approval_id: str,
    operator: str = "operator",
    note: str | None = None,
) -> ApprovalDecisionResponse:
    """Approve a pending action and execute it safely."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, action_type, description, parameters, status FROM approvals WHERE id = ?",
            (approval_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise KeyError(f"Approval '{approval_id}' not found.")
        if row["status"] != "pending":
            raise ValueError(f"Approval '{approval_id}' is already {row['status']}.")

        action_type = row["action_type"]
        parameters = json.loads(row["parameters"]) if row["parameters"] else {}
        now = datetime.now(timezone.utc).isoformat()

        # Execute the action safely
        execution_status = "executed"
        execution_result: dict[str, Any] = {}

        if action_type in {"create_incident_ticket", "telemetry__create_incident_ticket"}:
            title = parameters.get("title", "Incident Triage Ticket")
            severity = parameters.get("severity", "HIGH")
            summary = parameters.get("summary", "Automatically proposed triage ticket.")
            assignee = parameters.get("assignee", "oncall-team")

            ticket_cursor = conn.execute(
                """
                INSERT INTO incident_tickets (created_at, title, severity, summary, assignee)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now, title, severity, summary, assignee),
            )
            ticket_id_num = ticket_cursor.lastrowid + 1041
            ticket_id = f"INC-{ticket_id_num}"
            execution_result = {
                "ticket_id": ticket_id,
                "created_at": now,
                "title": title,
                "severity": severity,
                "summary": summary,
                "assignee": assignee,
            }
        elif action_type == "rollback_deployment":
            service_name = parameters.get("service_name", "unknown")
            target_version = parameters.get("target_version", "previous-stable")
            execution_result = {
                "service_name": service_name,
                "target_version": target_version,
                "rollback_status": "initiated",
                "timestamp": now,
            }
        else:
            execution_result = {
                "action": action_type,
                "status": "completed",
                "timestamp": now,
                "details": note or "Action executed upon human approval.",
            }

        conn.execute(
            """
            UPDATE approvals
            SET status = 'approved',
                decision_at = ?,
                decision_by = ?,
                execution_status = ?,
                execution_result = ?
            WHERE id = ?
            """,
            (now, operator, execution_status, json.dumps(execution_result), approval_id),
        )
        conn.commit()
    finally:
        conn.close()

    return ApprovalDecisionResponse(
        approval_id=approval_id,
        status="approved",
        action_type=action_type,
        execution_status=execution_status,
        execution_result=execution_result,
        message=f"Action '{action_type}' successfully approved and executed.",
    )


def reject_action(
    db_path: Path,
    approval_id: str,
    operator: str = "operator",
    reason: str | None = None,
) -> ApprovalDecisionResponse:
    """Reject a pending action without executing it."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, action_type, status FROM approvals WHERE id = ?",
            (approval_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise KeyError(f"Approval '{approval_id}' not found.")
        if row["status"] != "pending":
            raise ValueError(f"Approval '{approval_id}' is already {row['status']}.")

        action_type = row["action_type"]
        now = datetime.now(timezone.utc).isoformat()
        execution_result = {
            "rejection_reason": reason or "Rejected by operator.",
            "timestamp": now,
        }

        conn.execute(
            """
            UPDATE approvals
            SET status = 'rejected',
                decision_at = ?,
                decision_by = ?,
                execution_status = 'skipped',
                execution_result = ?
            WHERE id = ?
            """,
            (now, operator, json.dumps(execution_result), approval_id),
        )
        conn.commit()
    finally:
        conn.close()

    return ApprovalDecisionResponse(
        approval_id=approval_id,
        status="rejected",
        action_type=action_type,
        execution_status="skipped",
        execution_result=execution_result,
        message=f"Action '{action_type}' rejected. No mutating action was executed.",
    )
