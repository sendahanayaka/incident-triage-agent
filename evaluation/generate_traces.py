"""Generate authentic sample execution traces using the real agent orchestrator and MCP servers."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Ensure project roots are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_CLIENT_DIR = REPO_ROOT / "agent-client"
if str(AGENT_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_CLIENT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.benchmark_runner import build_mock_llm_handler, load_scenarios
from evaluation.evaluator import BenchmarkEvaluator
from httpx import AsyncClient, MockTransport
from mcp_tools import connect_agent_tools  # type: ignore[missing-import]
from openai import AsyncOpenAI
from orchestrator import investigate  # type: ignore[missing-import]

TRACES_DIR = REPO_ROOT / "traces"

TRACE_TARGETS = [
    {
        "scenario_id": "EVAL-02",
        "output_file": TRACES_DIR / "sample_root_cause_investigation.jsonl",
        "name": "Trace A: Successful Root Cause Investigation",
    },
    {
        "scenario_id": "EVAL-07",
        "output_file": TRACES_DIR / "sample_hitl_approved.jsonl",
        "name": "Trace B: Human-Approved Incident Ticket",
    },
    {
        "scenario_id": "EVAL-08",
        "output_file": TRACES_DIR / "sample_hitl_rejected.jsonl",
        "name": "Trace C: Human-Rejected Incident Ticket",
    },
    {
        "scenario_id": "EVAL-06",
        "output_file": TRACES_DIR / "sample_prompt_injection_defense.jsonl",
        "name": "Trace D: Prompt Injection Defense",
    },
]


async def generate_single_trace(
    scenario: dict[str, Any],
    output_path: Path,
    isolated_db_dir: Path,
) -> dict[str, Any]:
    """Execute real agent pipeline for a scenario and write trace to output_path."""
    scenario_id = scenario["scenario_id"]
    prompt = scenario["prompt"]
    approval_reqs = scenario.get("expected_approval_behavior", {})
    expected_decision = approval_reqs.get("expected_decision", "approved")
    requires_approval = approval_reqs.get("approval_required", False)

    temp_db_path = isolated_db_dir / f"trace_{scenario_id.lower()}_incidents.db"
    os.environ["OPS_TELEMETRY_TICKET_PATH"] = str(temp_db_path)

    # Ensure target trace file is fresh
    if output_path.exists():
        output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    approval_requested = False
    recorded_decision: str | None = None

    def trace_approval_cb(name: str, args: dict[str, Any]) -> bool:
        nonlocal approval_requested, recorded_decision
        approval_requested = True
        if requires_approval and expected_decision == "approved":
            recorded_decision = "approved"
            return True
        recorded_decision = "rejected"
        return False

    transport = MockTransport(build_mock_llm_handler(scenario))
    mock_http_client: Any = AsyncClient(transport=transport)
    llm = AsyncOpenAI(
        api_key="mock-key",
        base_url="https://model.invalid/v1",
        http_client=mock_http_client,
        max_retries=0,
    )

    try:
        async with connect_agent_tools() as tools:
            response = await investigate(
                prompt,
                llm,
                "mock-eval-model",
                tools,
                trace_path=output_path,
                max_iterations=8,
                tool_timeout=10,
                approval_callback=trace_approval_cb,
            )
    finally:
        await llm.close()

    return {
        "scenario_id": scenario_id,
        "output_path": output_path,
        "response": response,
        "approval_requested": approval_requested,
        "recorded_decision": recorded_decision,
    }


async def generate_all_sample_traces() -> list[dict[str, Any]]:
    """Generate all 4 authentic sample execution traces."""
    scenarios = {s["scenario_id"]: s for s in load_scenarios()}
    results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="agent_trace_run_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for target in TRACE_TARGETS:
            scen_id = target["scenario_id"]
            out_file = target["output_file"]
            print(f"Generating {target['name']} -> {out_file.name}...")
            res = await generate_single_trace(scenarios[scen_id], out_file, temp_dir)
            results.append(res)
            print(f"  [OK] Saved {out_file.name} ({out_file.stat().st_size} bytes)")
            print(f"  Final Response: {res['response']}\n")

    return results


def main() -> int:
    print("=" * 70)
    print(" GENERATING AUTHENTIC SAMPLE EXECUTION TRACES")
    print("=" * 70 + "\n")
    asyncio.run(generate_all_sample_traces())
    print("=" * 70)
    print(" All 4 sample execution traces generated successfully.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
