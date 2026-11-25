"""Run an incident investigation or release readiness check from the terminal."""

import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from dotenv import load_dotenv
from mcp import MCPError
from openai import APIError

from filesystem_mcp import REPO_ROOT
from llm_provider import get_llm_client, load_llm_config_from_env
from mcp_tools import connect_agent_tools
from orchestrator import cli_approval_prompt, investigate


async def run(
    question: str,
    approval_callback: Callable[[str, dict[str, Any]], bool | Awaitable[bool]] | None = None,
) -> str:
    load_dotenv(REPO_ROOT / ".env")
    if not question.strip():
        raise ValueError("Enter an incident triage or release readiness question.")

    config = load_llm_config_from_env()
    max_iterations = int(os.getenv("MAX_AGENT_ITERATIONS", "8"))
    tool_timeout = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "10"))
    trace_path = REPO_ROOT / os.getenv("TRACE_FILE_PATH", "traces/agent_traces.jsonl")

    cb = approval_callback or cli_approval_prompt

    llm, model = get_llm_client(config)
    async with llm:
        async with connect_agent_tools() as tools:
            return await investigate(
                question,
                llm,
                model,
                tools,
                trace_path=trace_path,
                max_iterations=max_iterations,
                tool_timeout=tool_timeout,
                approval_callback=cb,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="An incident triage or release readiness request.")
    args = parser.parse_args()
    try:
        print(asyncio.run(run(args.question)))
    except (APIError, MCPError, OSError, RuntimeError, ValueError) as error:
        print(f"Agent: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
