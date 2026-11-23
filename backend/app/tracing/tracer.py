"""Trace reading, parsing, and sanitization for agent observability."""

import json
from pathlib import Path
from typing import Any

from backend.app.models.trace import TraceResponse

SENSITIVE_KEYS = frozenset({
    "api_key",
    "key",
    "secret",
    "token",
    "password",
    "authorization",
    "access_token",
})


def _sanitize_value(key: str, val: Any) -> Any:
    """Scrub sensitive keys and tokens from trace data."""
    if any(k in key.lower() for k in SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(val, dict):
        return {k: _sanitize_value(k, v) for k, v in val.items()}
    if isinstance(val, list):
        return [_sanitize_value(key, item) for item in val]
    if isinstance(val, str) and ("sk-" in val or "bearer " in val.lower()):
        return "[REDACTED]"
    return val


def _infer_mcp_server(tool_name: str) -> str:
    """Infer the originating MCP server from tool namespace."""
    if tool_name.startswith("telemetry__"):
        return "ops-telemetry-mcp (Rust)"
    if tool_name.startswith("filesystem__"):
        return "server-filesystem (Official MCP)"
    return "orchestrator"


def read_traces(trace_path: Path, run_id: str | None = None) -> list[TraceResponse]:
    """Read structured traces from JSONL trace storage with secret scrubbing."""
    if not trace_path.is_file():
        return []

    traces: list[TraceResponse] = []
    try:
        with trace_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        continue
                    event_run_id = raw.get("run_id", "")
                    if run_id and event_run_id != run_id:
                        continue

                    tool = raw.get("tool", "unknown")
                    raw_args = raw.get("arguments", {})
                    sanitized_args = _sanitize_value("arguments", raw_args)
                    if not isinstance(sanitized_args, dict):
                        sanitized_args = {"value": sanitized_args}

                    traces.append(
                        TraceResponse(
                            timestamp=raw.get("timestamp", ""),
                            run_id=event_run_id,
                            tool=tool,
                            arguments=sanitized_args,
                            duration_ms=float(raw.get("duration_ms", 0.0)),
                            status=raw.get("status", "ok"),
                            mcp_server=_infer_mcp_server(tool),
                        )
                    )
                except (json.JSONDecodeError, ValueError):
                    continue
    except OSError:
        return []

    return traces
