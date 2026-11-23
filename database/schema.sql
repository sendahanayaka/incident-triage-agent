-- ==============================================================================
-- SQLite Schema for Incident Triage & Release Readiness Agent
-- File: database/schema.sql
-- ==============================================================================

-- 1. Incident Tickets Table (Created & managed by Rust MCP server and Python approval gate)
CREATE TABLE IF NOT EXISTS incident_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    assignee TEXT NOT NULL
);

-- 2. Human-in-the-Loop Approvals Table (Audit ledger of proposed and decided actions)
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    parameters TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL, -- pending, approved, rejected
    created_at TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    decision_at TEXT,
    decision_by TEXT,
    execution_status TEXT NOT NULL, -- pending, executed, skipped, failed
    execution_result TEXT
);

-- 3. Investigations Table (Record of completed and in-progress agent triage runs)
CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    status TEXT NOT NULL, -- completed, failed, in_progress
    findings TEXT NOT NULL,
    evidence TEXT NOT NULL,
    recommendations TEXT NOT NULL,
    tool_calls TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error_message TEXT
);
