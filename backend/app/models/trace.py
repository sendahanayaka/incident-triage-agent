"""Agent trace models."""

from typing import Any
from pydantic import BaseModel, Field


class TraceResponse(BaseModel):
    """Execution trace event emitted by the agent orchestrator."""

    timestamp: str = Field(..., description="UTC ISO timestamp of event")
    run_id: str = Field(..., description="Investigation run identifier")
    tool: str = Field(..., description="Tool or action executed")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool input arguments")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    status: str = Field(..., description="Execution status: ok, error, timeout")
    mcp_server: str | None = Field(default=None, description="Inferred MCP server origin")


class TracesListResponse(BaseModel):
    """List of agent execution traces."""

    traces: list[TraceResponse] = Field(default_factory=list)
    total: int = Field(default=0)
