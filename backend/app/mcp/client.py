"""MCP Client wrapper interfacing with the existing agent-client MCP implementations."""

import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from backend.app.core.config import REPO_ROOT

# Ensure agent-client directory is in Python path for reuse
AGENT_CLIENT_DIR = str(REPO_ROOT / "agent-client")
if AGENT_CLIENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_CLIENT_DIR)

from mcp_tools import AgentTools, connect_agent_tools
from filesystem_mcp import WorkspaceFilesystem, connect_filesystem


@asynccontextmanager
async def get_mcp_tools() -> AsyncIterator[AgentTools]:
    """Context manager to connect and discover agent MCP tools."""
    async with connect_agent_tools() as tools:
        yield tools


@asynccontextmanager
async def get_filesystem_tools() -> AsyncIterator[WorkspaceFilesystem]:
    """Context manager to connect to the official filesystem MCP server."""
    async with connect_filesystem() as filesystem:
        yield filesystem
