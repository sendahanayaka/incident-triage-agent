"""Benchmark runner for the Incident Triage & Release Readiness Agent."""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from httpx import AsyncClient, MockTransport, Request, Response
from openai import AsyncOpenAI

# Ensure agent-client and evaluation are importable
REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_CLIENT_DIR = REPO_ROOT / "agent-client"
if str(AGENT_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_CLIENT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.evaluator import BenchmarkEvaluator
from evaluation.metrics import AggregateMetrics, ScenarioResult, calculate_aggregate_metrics
from mcp_tools import connect_agent_tools  # type: ignore[missing-import]
from orchestrator import investigate  # type: ignore[missing-import]

SCENARIOS_FILE = REPO_ROOT / "evaluation" / "scenarios" / "benchmark_scenarios.json"


def load_scenarios(path: Path = SCENARIOS_FILE) -> list[dict[str, Any]]:
    """Load and validate benchmark scenario definitions from JSON."""
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark scenarios file not found at: {path}")
    with path.open("r", encoding="utf-8") as f:
        scenarios = json.load(f)
    if not isinstance(scenarios, list):
        raise ValueError("Benchmark scenarios JSON must contain a list of scenarios.")
    for s in scenarios:
        if "scenario_id" not in s or "prompt" not in s:
            raise ValueError(f"Scenario missing required keys ('scenario_id', 'prompt'): {s}")
    return scenarios


def create_mock_completion(*calls: dict[str, Any], summary: str | None = None) -> Response:
    """Helper to build a valid OpenAI ChatCompletion response."""
    message: dict[str, Any] = {"role": "assistant", "content": summary}
    if calls:
        message["tool_calls"] = list(calls)
    return Response(
        200,
        json={
            "id": f"mock_cmpl_{uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(monotonic()),
            "model": "mock-eval-model",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if calls else "stop",
                }
            ],
        },
    )


def build_mock_llm_handler(scenario: dict[str, Any]):
    """Construct a deterministic MockTransport handler simulating agent turns for a scenario."""
    scenario_id = scenario["scenario_id"]
    step = 0

    def handler(request: Request) -> Response:
        nonlocal step
        step += 1
        payload = json.loads(request.content)
        messages = payload.get("messages", [])

        if scenario_id == "EVAL-01":
            if step == 1:
                return create_mock_completion({
                    "id": "call_eval01_1",
                    "type": "function",
                    "function": {
                        "name": "telemetry__get_deployment_history",
                        "arguments": json.dumps({"service_name": "auth-service", "window_hours": 24}),
                    },
                })
            return create_mock_completion(
                summary="The latest deployment for auth-service is auth-087 (version 1.8.4), which refreshed the staging signing-key cache."
            )

        elif scenario_id == "EVAL-02":
            if step == 1:
                return create_mock_completion(
                    {
                        "id": "call_eval02_1",
                        "type": "function",
                        "function": {
                            "name": "telemetry__search_logs",
                            "arguments": json.dumps({"service_name": "payments-api", "severity": "ERROR", "limit": 5}),
                        },
                    },
                    {
                        "id": "call_eval02_2",
                        "type": "function",
                        "function": {
                            "name": "telemetry__get_deployment_history",
                            "arguments": json.dumps({"service_name": "payments-api", "window_hours": 24}),
                        },
                    },
                )
            return create_mock_completion(
                summary="Investigation reveals that candidate deployment pay-204 lowered the gateway timeout to 250 ms, causing repeated gateway_timeout errors on payments-api."
            )

        elif scenario_id == "EVAL-03":
            if step == 1:
                return create_mock_completion({
                    "id": "call_eval03_1",
                    "type": "function",
                    "function": {
                        "name": "telemetry__get_deployment_history",
                        "arguments": json.dumps({"service_name": "notification-worker", "window_hours": 24}),
                    },
                })
            return create_mock_completion(
                summary="Notification-worker is running deployment notify-116 (version 3.1.2). Logs show the queue depth is 0 and smoke tests pass. Service is ready for release."
            )

        elif scenario_id == "EVAL-04":
            if step == 1:
                return create_mock_completion({
                    "id": "call_eval04_1",
                    "type": "function",
                    "function": {
                        "name": "telemetry__search_logs",
                        "arguments": json.dumps({"service_name": "nonexistent-service-xyz", "limit": 5}),
                    },
                })
            return create_mock_completion(
                summary="Service nonexistent-service-xyz was not found in telemetry. It is an unknown service with no logs or deployments."
            )

        elif scenario_id == "EVAL-05":
            return create_mock_completion(
                summary="The investigation request is ambiguous. Which service are you observing errors on? Please clarify the target service and symptoms."
            )

        elif scenario_id == "EVAL-06":
            if step == 1:
                return create_mock_completion({
                    "id": "call_eval06_1",
                    "type": "function",
                    "function": {
                        "name": "telemetry__search_logs",
                        "arguments": json.dumps({"service_name": "payments-api", "severity": "ERROR", "limit": 5}),
                    },
                })
            return create_mock_completion(
                summary="Error logs indicate authorization probes failed due to gateway timeouts following deployment pay-204 (250 ms timeout). The embedded instruction in LOG-019 was ignored and the release is blocked."
            )

        elif scenario_id == "EVAL-07":
            if step == 1:
                return create_mock_completion({
                    "id": "call_eval07_1",
                    "type": "function",
                    "function": {
                        "name": "telemetry__create_incident_ticket",
                        "arguments": json.dumps({
                            "title": "payments-api repeated gateway timeouts",
                            "severity": "CRITICAL",
                            "summary": "Payments authorization probes failing following pay-204 deployment",
                            "assignee": "payments-oncall",
                        }),
                    },
                })
            return create_mock_completion(
                summary="Approved incident ticket created successfully for payments-api outage."
            )

        elif scenario_id == "EVAL-08":
            if step == 1:
                return create_mock_completion({
                    "id": "call_eval08_1",
                    "type": "function",
                    "function": {
                        "name": "telemetry__create_incident_ticket",
                        "arguments": json.dumps({
                            "title": "payments-api gateway timeout ticket",
                            "severity": "HIGH",
                            "summary": "Gateway timeout investigation",
                            "assignee": "payments-oncall",
                        }),
                    },
                })
            return create_mock_completion(
                summary="The proposal to create an incident ticket was rejected by operator. The ticket was not created."
            )

        # Default fallback
        return create_mock_completion(summary="Completed investigation.")

    return handler


async def run_scenario(
    scenario: dict[str, Any],
    evaluator: BenchmarkEvaluator,
    *,
    use_live_llm: bool = False,
    isolated_db_dir: Path | None = None,
) -> ScenarioResult:
    """Execute a single benchmark scenario and return evaluated results."""
    scenario_id = scenario["scenario_id"]
    prompt = scenario["prompt"]
    approval_reqs = scenario.get("expected_approval_behavior", {})
    expected_decision = approval_reqs.get("expected_decision", "approved")
    requires_approval = approval_reqs.get("approval_required", False)

    # Isolated SQLite database and trace file
    temp_dir = isolated_db_dir or Path(tempfile.mkdtemp(prefix="agent_eval_"))
    temp_db_path = temp_dir / f"test_{scenario_id.lower()}_incidents.db"
    temp_trace_path = temp_dir / f"test_{scenario_id.lower()}_traces.jsonl"

    # Set Rust MCP ticket store override to guarantee database isolation
    os.environ["OPS_TELEMETRY_TICKET_PATH"] = str(temp_db_path)

    approval_requested = False
    recorded_decision: str | None = None

    def mock_approval_cb(name: str, args: dict[str, Any]) -> bool:
        nonlocal approval_requested, recorded_decision
        approval_requested = True
        if requires_approval and expected_decision == "approved":
            recorded_decision = "approved"
            return True
        recorded_decision = "rejected"
        return False

    tool_calls_executed: list[dict[str, Any]] = []

    # Configure LLM Client
    if use_live_llm:
        load_dotenv(REPO_ROOT / ".env")
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        if not api_key:
            raise ValueError("Live LLM mode requested but LLM_API_KEY is not set.")
        llm = AsyncOpenAI(api_key=api_key, base_url=os.getenv("LLM_BASE_URL") or None, timeout=30)
    else:
        model = "mock-eval-model"
        transport = MockTransport(build_mock_llm_handler(scenario))
        mock_http_client: Any = AsyncClient(transport=transport)
        llm = AsyncOpenAI(
            api_key="mock-key",
            base_url="https://model.invalid/v1",
            http_client=mock_http_client,
            max_retries=0,
        )

    started = monotonic()
    try:
        async with connect_agent_tools() as tools:
            # Wrap tool calls to observe names and arguments
            orig_call = tools.call

            async def observing_call(name: str, arguments: dict[str, Any], *, approval_token: str | None = None):
                tool_calls_executed.append({"name": name, "arguments": arguments})
                return await orig_call(name, arguments, approval_token=approval_token)

            tools.call = observing_call  # type: ignore[method-assign]

            response = await investigate(
                prompt,
                llm,
                model,
                tools,
                trace_path=temp_trace_path,
                max_iterations=8,
                tool_timeout=10,
                approval_callback=mock_approval_cb,
            )
    finally:
        await llm.close()

    duration_ms = (monotonic() - started) * 1000.0

    # Load trace events
    trace_events: list[dict[str, Any]] = []
    if temp_trace_path.exists():
        with temp_trace_path.open("r", encoding="utf-8") as tf:
            for line in tf:
                line = line.strip()
                if line:
                    try:
                        trace_events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Count tickets created in isolated DB
    tickets_count = 0
    if temp_db_path.exists():
        try:
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM incident_tickets")
            row = cursor.fetchone()
            if row:
                tickets_count = int(row[0])
            conn.close()
        except sqlite3.OperationalError:
            tickets_count = 0

    iterations = len(trace_events)

    return evaluator.evaluate(
        scenario=scenario,
        response=response,
        tool_calls=tool_calls_executed,
        trace_events=trace_events,
        duration_ms=duration_ms,
        iterations=iterations,
        approval_requested=approval_requested,
        approval_decision=recorded_decision,
        tickets_created=tickets_count,
    )


async def run_benchmark(
    scenario_ids: list[str] | None = None,
    output_path: Path | None = None,
    use_live_llm: bool = False,
) -> AggregateMetrics:
    """Execute the benchmark suite across specified or all scenarios."""
    scenarios = load_scenarios()
    if scenario_ids:
        scenarios = [s for s in scenarios if s["scenario_id"] in scenario_ids]
        if not scenarios:
            raise ValueError(f"No scenarios matched IDs: {scenario_ids}")

    evaluator = BenchmarkEvaluator()
    results: list[ScenarioResult] = []
    run_id = f"eval_run_{uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    with tempfile.TemporaryDirectory(prefix="agent_eval_suite_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for s in scenarios:
            res = await run_scenario(
                s,
                evaluator,
                use_live_llm=use_live_llm,
                isolated_db_dir=temp_dir,
            )
            results.append(res)

    aggregate = calculate_aggregate_metrics(run_id, timestamp, results)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as out:
            json.dump(aggregate.to_dict(), out, indent=2)

    return aggregate


def print_benchmark_summary(metrics: AggregateMetrics) -> None:
    """Format and print a human-readable terminal benchmark summary."""
    print("\n" + "=" * 78)
    print(f" AGENT BENCHMARK EVALUATION REPORT  [{metrics.run_id}]")
    print("=" * 78)
    print(f"Timestamp:              {metrics.timestamp}")
    print(f"Total Scenarios:        {metrics.total_scenarios}")
    print(f"Passed:                 {metrics.passed} / {metrics.total_scenarios} ({metrics.scenario_success_rate:.1f}%)")
    print(f"Overall Benchmark Score:{metrics.overall_benchmark_score:.1f} / 100")
    print("-" * 78)
    print(f"Tool Selection Accuracy:{metrics.tool_selection_accuracy:.1f}%")
    print(f"Investigation Correct.: {metrics.investigation_correctness:.1f}%")
    print(f"Safety Compliance:      {metrics.safety_compliance:.1f}%")
    print(f"HITL Compliance:        {metrics.hitl_compliance:.1f}%")
    print(f"Autonomous Success Rate:{metrics.autonomous_success_rate:.1f}% ({metrics.autonomous_passed}/{metrics.autonomous_total})")
    print(f"Human-Assisted Success: {metrics.human_assisted_success_rate:.1f}% ({metrics.human_assisted_passed}/{metrics.human_assisted_total})")
    print(f"Average Latency:        {metrics.average_latency_ms:.1f} ms")
    print(f"Critical Safety Viol.:  {metrics.critical_safety_violations_count}")
    print("=" * 78)

    print("\nSCENARIO BREAKDOWN:")
    print("-" * 78)
    print(f"{'ID':<9} {'Scenario Name':<28} {'Type':<10} {'Score':<8} {'Status':<8}")
    print("-" * 78)
    for sr in metrics.scenario_results:
        st_label = "PASS" if sr["score"]["passed"] else "FAIL"
        auto_label = "Auto" if sr["is_autonomous"] else "HITL"
        sc_num = f"{sr['score']['overall_score']*100:.0f}%"
        print(f"{sr['scenario_id']:<9} {sr['scenario_name'][:26]:<28} {auto_label:<10} {sc_num:<8} {st_label:<8}")
        if sr["score"]["failure_reasons"]:
            for r in sr["score"]["failure_reasons"]:
                print(f"   -> Note: {r}")
    print("=" * 78 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Run all 8 benchmark scenarios.")
    parser.add_argument("--scenario", "-s", type=str, help="Specific scenario ID to run (e.g. EVAL-02).")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=REPO_ROOT / "evaluation" / "results" / "latest.json",
        help="Path for saving evaluation metrics JSON.",
    )
    parser.add_argument("--live", action="store_true", help="Execute using live configured LLM API.")
    args = parser.parse_args()

    scenario_ids = None
    if args.scenario:
        scenario_ids = [args.scenario.strip().upper()]
    elif not args.all:
        scenario_ids = None  # default to all

    metrics = asyncio.run(run_benchmark(scenario_ids=scenario_ids, output_path=args.output, use_live_llm=args.live))
    print_benchmark_summary(metrics)
    return 0 if metrics.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
