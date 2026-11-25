"""Agent orchestrator integration for executing incident investigations."""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from openai import AsyncOpenAI

from backend.app.core.config import REPO_ROOT, Settings, settings
from backend.app.models.investigation import InvestigationResponse, ToolCallRecord

# Ensure agent-client directory is in Python path for reuse
AGENT_CLIENT_DIR = str(REPO_ROOT / "agent-client")
if AGENT_CLIENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_CLIENT_DIR)

from llm_provider import (
    LLMConfig,
    get_llm_client,
    validate_live_openrouter_config,
)
from mcp_tools import connect_agent_tools
from orchestrator import investigate


def _extract_root_cause(exc: BaseException) -> tuple[str, list[str]]:
    """Recursively unwrap nested ExceptionGroups to extract root error and user-friendly explanation."""
    current = exc
    while hasattr(current, "exceptions") and getattr(current, "exceptions", None):
        exceptions = getattr(current, "exceptions")
        if exceptions:
            current = exceptions[0]
        else:
            break
    raw_msg = str(current)
    if "429" in raw_msg or "quota" in raw_msg.lower() or "resource_exhausted" in raw_msg.lower():
        msg = (
            "Google Gemini API Free-Tier Quota Limit Exceeded (429 RESOURCE_EXHAUSTED): "
            "Google AI Studio enforces a strict daily limit (20 requests/day) for this free API key, "
            "which has been reached for today. "
            "To continue testing and evaluating the agent immediately without waiting for the 24-hour quota reset, "
            "switch to offline mode by setting `LLM_MODE=offline` in `.env` (or provide an OpenRouter/Gemini key with active paid/tier-1 quota)."
        )
        recommendations = [
            "Set LLM_MODE=offline in .env for zero-cost, unlimited ReAct triage testing.",
            "Restart backend with: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000",
            "Or upgrade Google AI Studio key / configure OpenRouter key with active quota in .env.",
        ]
        return msg, recommendations
    return (
        f"{type(current).__name__}: {raw_msg}",
        ["Verify LLM_API_KEY, LLM_MODEL, and MCP server configuration."],
    )


def _extract_citations(text: str) -> list[str]:
    """Extract log, deployment, service, or resource citations from text."""
    evidence = []
    log_matches = re.findall(r"\bLOG-\d+\b", text)
    evidence.extend(sorted(set(log_matches)))
    dep_matches = re.findall(r"\b(?:pay|auth|notify|[a-z]+)-\d+\b", text)
    evidence.extend(sorted(set(dep_matches)))
    uri_matches = re.findall(r"(?:service://runbooks/[\w-]+|config://[\w-]+|[\w-]+\.(?:md|yaml|json))", text)
    evidence.extend(sorted(set(uri_matches)))
    svc_matches = re.findall(r"Target service:\s*`?([a-zA-Z0-9_-]+(?:-api|-service|-worker))`?", text)
    evidence.extend(sorted(set(svc_matches)))
    return evidence


def _load_recent_tool_calls(trace_path: Path, run_id: str | None = None) -> list[ToolCallRecord]:
    """Read tool call events from the trace file for this specific run."""
    tool_calls: list[ToolCallRecord] = []
    if trace_path.is_file():
        with trace_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if run_id and record.get("run_id") != run_id:
                        continue

                    raw_args = record.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except Exception:
                            raw_args = {"raw": raw_args}
                    elif not isinstance(raw_args, dict):
                        raw_args = {"raw": str(raw_args)}

                    tool_calls.append(
                        ToolCallRecord(
                            tool=record.get("tool", "unknown"),
                            arguments=raw_args,
                            status=record.get("status", "ok"),
                            duration_ms=record.get("duration_ms"),
                        )
                    )
                except (json.JSONDecodeError, ValueError):
                    continue
    return tool_calls


async def execute_investigation(
    query: str,
    app_settings: Settings = settings,
) -> InvestigationResponse:
    """Run an incident triage or release readiness investigation."""
    investigation_id = f"inv-{uuid4().hex[:8]}"
    run_id = f"run-{uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    trace_path = app_settings.resolved_trace_file_path

    # Track approvals created specifically within this investigation run
    run_approvals: list[Any] = []

    async def local_approval_callback(name: str, arguments: dict[str, Any]) -> bool:
        """Non-blocking approval handler for Web backend: registers pending approval in SQLite."""
        from backend.app.approvals.manager import create_approval

        db_path = app_settings.resolved_database_path
        risk = "HIGH" if "CRITICAL" in str(arguments).upper() else "MEDIUM"
        desc = f"Agent proposes executing mutation action '{name}' for incident remediation."
        raw_args = arguments if isinstance(arguments, dict) else {"raw": arguments}
        try:
            app_record = create_approval(
                db_path,
                action_type=name,
                description=desc,
                parameters=raw_args,
                risk_level=risk,
                requested_by="incident-triage-agent",
            )
            run_approvals.append(app_record)
        except Exception:
            pass
        # Held in pending state for human operator review in the Web UI
        return False

    llm_config = LLMConfig(
        provider=app_settings.llm_provider,
        mode=app_settings.llm_mode,
        model=app_settings.llm_model,
        api_key=app_settings.llm_api_key,
        base_url=app_settings.llm_base_url,
    )

    # 1. Live mode execution with configured provider (OpenRouter or Gemini)
    if llm_config.is_live:
        try:
            validate_live_openrouter_config(llm_config)
            llm, model_name = get_llm_client(llm_config)
            try:
                async with connect_agent_tools() as tools:
                    summary = await investigate(
                        query,
                        llm,
                        model_name,
                        tools,
                        trace_path=trace_path,
                        max_iterations=app_settings.max_agent_iterations,
                        tool_timeout=app_settings.agent_tool_timeout_seconds,
                        approval_callback=local_approval_callback,
                        run_id=run_id,
                    )
            finally:
                await llm.close()

            completed_at = datetime.now(timezone.utc).isoformat()
            evidence = _extract_citations(summary)
            tool_calls = _load_recent_tool_calls(trace_path, run_id=run_id)

            return InvestigationResponse(
                id=investigation_id,
                query=query,
                status="completed",
                findings=summary,
                evidence=evidence,
                recommendations=[
                    "Inspect affected service logs and deployment differences.",
                    "Verify runbook mitigation steps before state mutation.",
                ],
                tool_calls=tool_calls,
                pending_approval=run_approvals[0] if run_approvals else None,
                created_at=created_at,
                completed_at=completed_at,
            )
        except Exception as exc:
            completed_at = datetime.now(timezone.utc).isoformat()
            err_msg, recommendations = _extract_root_cause(exc)
            logger.error("Live investigation failed: %s", err_msg, exc_info=True)
            return InvestigationResponse(
                id=investigation_id,
                query=query,
                status="failed",
                findings=f"Live LLM investigation failed: {err_msg}",
                evidence=[],
                recommendations=recommendations,
                tool_calls=[],
                created_at=created_at,
                completed_at=completed_at,
            )

    # 2. Offline deterministic mode: Execute real ReAct loop via offline transport & connected MCP tools
    try:
        llm, model_name = get_llm_client(llm_config)
        try:
            async with connect_agent_tools() as tools:
                summary = await investigate(
                    query,
                    llm,
                    model_name,
                    tools,
                    trace_path=trace_path,
                    max_iterations=app_settings.max_agent_iterations,
                    tool_timeout=app_settings.agent_tool_timeout_seconds,
                    approval_callback=local_approval_callback,
                    run_id=run_id,
                )
                completed_at = datetime.now(timezone.utc).isoformat()
                evidence = _extract_citations(summary)
                tool_calls = _load_recent_tool_calls(trace_path, run_id=run_id)
                return InvestigationResponse(
                    id=investigation_id,
                    query=query,
                    status="completed",
                    findings=summary,
                    evidence=evidence,
                    recommendations=[
                        "Inspect affected service logs and deployment differences.",
                        "Verify runbook mitigation steps before state mutation.",
                    ],
                    tool_calls=tool_calls,
                    pending_approval=run_approvals[0] if run_approvals else None,
                    created_at=created_at,
                    completed_at=completed_at,
                )
        finally:
            await llm.close()
    except Exception as exc:
        completed_at = datetime.now(timezone.utc).isoformat()
        err_msg, recommendations = _extract_root_cause(exc)
        logger.error("Offline investigation failed: %s", err_msg, exc_info=True)
        return InvestigationResponse(
            id=investigation_id,
            query=query,
            status="failed",
            findings=f"Investigation failed: {err_msg}",
            evidence=[],
            recommendations=[
                "Ensure Rust ops-telemetry-mcp server binary is built (cargo build in mcp-server).",
                "Ensure Node.js filesystem MCP server is reachable.",
            ],
            tool_calls=[],
            created_at=created_at,
            completed_at=completed_at,
        )
