"""Discover and route the MCP capabilities available to an investigation."""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent, TextResourceContents

from filesystem_mcp import REPO_ROOT, connect_filesystem

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class AgentTools:
    definitions: list[dict[str, Any]] = field(default_factory=list)
    _handlers: dict[str, ToolHandler] = field(default_factory=dict)

    def register(
        self, name: str, description: str, schema: dict[str, Any], handler: ToolHandler
    ) -> None:
        if name in self._handlers:
            raise ValueError(f"Duplicate agent tool {name!r}.")
        self._handlers[name] = handler
        self.definitions.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": schema,
                "strict": False,
            },
        })

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = self._handlers.get(name)
        if handler is None:
            raise PermissionError(f"Tool {name!r} is unavailable to this investigation.")
        return await handler(arguments)


async def _discover(list_page: Callable[..., Awaitable[Any]], field_name: str) -> AsyncIterator[Any]:
    cursor = None
    while True:
        page = await list_page(cursor=cursor)
        for item in getattr(page, field_name):
            yield item
        cursor = page.next_cursor
        if cursor is None:
            return


async def _call_tool(
    call: Callable[..., Awaitable[CallToolResult]], name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    result = await call(name, arguments)
    data = result.structured_content
    if data is None:
        data = [block.text for block in result.content if isinstance(block, TextContent)]
    return {"ok": not result.is_error, "data": data}


async def _read_resource(
    telemetry: Client, uris: frozenset[str], arguments: dict[str, Any]
) -> dict[str, Any]:
    uri = arguments.get("uri")
    if set(arguments) != {"uri"} or not isinstance(uri, str) or uri not in uris:
        raise ValueError("uri must identify a resource discovered on the telemetry server.")
    resource = await telemetry.read_resource(uri)
    return {
        "ok": True,
        "data": [
            {"uri": str(item.uri), "text": item.text}
            for item in resource.contents
            if isinstance(item, TextResourceContents)
        ],
    }


def _telemetry_parameters() -> StdioServerParameters:
    executable = "ops-telemetry-mcp.exe" if os.name == "nt" else "ops-telemetry-mcp"
    override = os.getenv("RUST_MCP_SERVER_PATH")
    path = REPO_ROOT / (override or f"mcp-server/target/debug/{executable}")
    if not path.is_file():
        raise FileNotFoundError(
            f"Telemetry server executable not found at {path}. Build the Rust server first."
        )
    overrides = {
        name: os.environ[name]
        for name in ("OPS_TELEMETRY_DATA_DIR", "OPS_TELEMETRY_REFERENCE_TIME")
        if name in os.environ
    }
    return StdioServerParameters(command=str(Path(path).resolve()), cwd=REPO_ROOT, env=overrides)


@asynccontextmanager
async def connect_agent_tools() -> AsyncIterator[AgentTools]:
    async with Client(_telemetry_parameters(), read_timeout_seconds=15) as telemetry:
        async with connect_filesystem() as filesystem:
            tools = AgentTools()
            async for tool in _discover(telemetry.list_tools, "tools"):
                if tool.annotations and tool.annotations.read_only_hint is True:
                    tools.register(
                        f"telemetry__{tool.name}", tool.description or tool.name,
                        tool.input_schema, partial(_call_tool, telemetry.call_tool, tool.name),
                    )
            for tool in filesystem.tools:
                tools.register(
                    f"filesystem__{tool.name}", tool.description or tool.name,
                    tool.input_schema, partial(_call_tool, filesystem.call_tool, tool.name),
                )

            resources = [resource async for resource in _discover(telemetry.list_resources, "resources")]
            if resources:
                resource_descriptions = [
                    f"{resource.uri} ({resource.description or resource.name})"
                    for resource in resources
                ]
                uris = frozenset(str(resource.uri) for resource in resources)
                tools.register(
                    "telemetry__read_resource",
                    "Read a discovered telemetry resource. Available resources: "
                    + "; ".join(resource_descriptions),
                    {
                        "type": "object",
                        "properties": {"uri": {"type": "string", "enum": sorted(uris)}},
                        "required": ["uri"],
                        "additionalProperties": False,
                    },
                    partial(_read_resource, telemetry, uris),
                )
            yield tools
