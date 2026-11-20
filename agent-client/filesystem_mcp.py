"""Read the release workspace through the official filesystem MCP server."""

import argparse
import asyncio
import os
import shutil
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import Client, MCPError, StdioServerParameters
from mcp.types import CallToolResult, TextContent, Tool

CLIENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CLIENT_DIR.parent
WORKSPACE_DIR = REPO_ROOT / "mock_data" / "workspace"
SERVER_ENTRY = CLIENT_DIR / "node_modules/@modelcontextprotocol/server-filesystem/dist/index.js"
PATH_TOOLS = frozenset({"list_directory", "read_text_file"})
WORKSPACE_TOOLS = PATH_TOOLS | {"list_allowed_directories"}


def configured_workspace() -> Path:
    workspace = WORKSPACE_DIR.resolve(strict=True)
    if workspace != WORKSPACE_DIR or not workspace.is_dir():
        raise ValueError("mock_data/workspace must be a directory inside this repository.")

    configured = REPO_ROOT / os.environ.get("FILESYSTEM_WORKSPACE", "mock_data/workspace")
    if configured.resolve() != workspace:
        raise ValueError("FILESYSTEM_WORKSPACE must point to this repository's mock_data/workspace.")
    return workspace


def filesystem_server_parameters() -> StdioServerParameters:
    workspace = configured_workspace()
    if not SERVER_ENTRY.is_file():
        raise FileNotFoundError("Install the filesystem server with npm ci in agent-client.")
    node = shutil.which("node")
    if node is None:
        raise FileNotFoundError("Node.js 24 or newer must be on PATH.")
    return StdioServerParameters(
        command=node,
        args=[str(SERVER_ENTRY), "--read-only", "--confine-roots", str(workspace)],
        cwd=workspace,
    )


@dataclass(frozen=True)
class WorkspaceFilesystem:
    workspace: Path
    tools: tuple[Tool, ...]
    _client: Client

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> CallToolResult:
        if not any(tool.name == name for tool in self.tools):
            raise PermissionError(f"Filesystem tool {name!r} is unavailable to the agent.")

        args = arguments or {}
        if name in PATH_TOOLS:
            path = args.get("path")
            if not isinstance(path, str) or not path.strip():
                raise ValueError(f"{name} requires a non-empty path.")
            candidate = (self.workspace / path).resolve()
            if not candidate.is_relative_to(self.workspace):
                raise PermissionError("The requested path is outside mock_data/workspace.")
            args = {**args, "path": str(candidate)}
        return await self._client.call_tool(name, args)


@asynccontextmanager
async def connect_filesystem() -> AsyncIterator[WorkspaceFilesystem]:
    parameters = filesystem_server_parameters()
    async with Client(parameters, read_timeout_seconds=10) as client:
        discovered = (await client.list_tools()).tools
        tools = tuple(
            tool for tool in discovered
            if tool.name in WORKSPACE_TOOLS
            and tool.annotations is not None
            and tool.annotations.read_only_hint is True
        )
        if {tool.name for tool in tools} != WORKSPACE_TOOLS:
            raise RuntimeError("The filesystem server did not advertise the required read-only tools.")

        filesystem = WorkspaceFilesystem(WORKSPACE_DIR, tools, client)
        result = await filesystem.call_tool("list_allowed_directories")
        content = (result.structured_content or {}).get("content")
        if result.is_error or not isinstance(content, str):
            raise RuntimeError("Could not verify the filesystem server's allowed directory.")
        header, _, directories = content.partition("\n")
        allowed = [Path(path) for path in directories.splitlines()]
        if header != "Allowed directories:" or allowed != [filesystem.workspace]:
            raise RuntimeError("The filesystem server must allow exactly mock_data/workspace.")
        yield filesystem


async def run_cli(action: str, path: str | None) -> int:
    async with connect_filesystem() as filesystem:
        if action == "tools":
            for tool in filesystem.tools:
                print(tool.name)
            return 0
        if action == "list":
            result = await filesystem.call_tool("list_directory", {"path": "."})
        else:
            result = await filesystem.call_tool("read_text_file", {"path": path})

        output = sys.stderr if result.is_error else sys.stdout
        for block in result.content:
            if isinstance(block, TextContent):
                print(block.text, file=output)
        return int(bool(result.is_error))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("tools", help="List filesystem tools available to the agent.")
    actions.add_parser("list", help="List files in the release workspace.")
    read = actions.add_parser("read", help="Read a text file from the release workspace.")
    read.add_argument("path")
    args = parser.parse_args()
    try:
        return asyncio.run(run_cli(args.action, getattr(args, "path", None)))
    except (OSError, ValueError, RuntimeError, MCPError) as error:
        print(f"Filesystem MCP: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
