"""Tests for agent traces endpoints."""

import json
from fastapi.testclient import TestClient
from backend.app.core.config import Settings


def test_get_traces_empty(client: TestClient) -> None:
    """Verify GET /api/traces returns empty list when no trace file exists."""
    response = client.get("/api/traces")
    assert response.status_code == 200
    assert response.json() == []


def test_get_traces_populated(client: TestClient, test_settings: Settings) -> None:
    """Verify GET /api/traces returns sanitized traces."""
    trace_path = test_settings.resolved_trace_file_path
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "timestamp": "2026-11-23T10:00:00Z",
            "run_id": "run-001",
            "tool": "telemetry__search_logs",
            "arguments": {"service_name": "payments-api", "severity": "ERROR", "api_key": "sk-secret123"},
            "duration_ms": 15.2,
            "status": "ok",
        },
        {
            "timestamp": "2026-11-23T10:00:02Z",
            "run_id": "run-002",
            "tool": "filesystem__read_text_file",
            "arguments": {"path": "RELEASE_NOTES.md"},
            "duration_ms": 5.4,
            "status": "ok",
        },
    ]

    with trace_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    response = client.get("/api/traces")
    assert response.status_code == 200
    traces = response.json()
    assert len(traces) == 2

    # Verify secret scrubbing
    first_trace = traces[0]
    assert first_trace["run_id"] == "run-001"
    assert first_trace["mcp_server"] == "ops-telemetry-mcp (Rust)"
    assert first_trace["arguments"]["api_key"] == "[REDACTED]"

    second_trace = traces[1]
    assert second_trace["mcp_server"] == "server-filesystem (Official MCP)"


def test_get_traces_filter_by_run_id(client: TestClient, test_settings: Settings) -> None:
    """Verify filtering traces by run_id or investigation_id."""
    trace_path = test_settings.resolved_trace_file_path
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    with trace_path.open("w", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "timestamp": "2026-11-23T10:00:00Z",
                "run_id": "run-abc",
                "tool": "telemetry__search_logs",
                "arguments": {"service_name": "payments-api"},
                "duration_ms": 10.0,
                "status": "ok",
            }) + "\n"
        )
        f.write(
            json.dumps({
                "timestamp": "2026-11-23T10:00:01Z",
                "run_id": "run-xyz",
                "tool": "filesystem__read_text_file",
                "arguments": {"path": "config.yaml"},
                "duration_ms": 4.0,
                "status": "ok",
            }) + "\n"
        )

    response = client.get("/api/traces?investigation_id=run-abc")
    assert response.status_code == 200
    traces = response.json()
    assert len(traces) == 1
    assert traces[0]["run_id"] == "run-abc"
