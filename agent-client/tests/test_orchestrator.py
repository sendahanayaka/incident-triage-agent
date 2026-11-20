import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from httpx import AsyncClient, MockTransport, Request, Response
from openai import AsyncOpenAI

from mcp_tools import AgentTools, connect_agent_tools
from orchestrator import investigate


def tool_call(index: int, name: str, arguments: str) -> dict:
    return {
        "id": f"call_{index}",
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def completion(*calls: dict, summary: str | None = None) -> Response:
    message = {"role": "assistant", "content": summary}
    if calls:
        message["tool_calls"] = calls
    return Response(200, json={
        "id": "mock_completion",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": "tool_calls" if calls else "stop",
        }],
    })


def model_client(handler) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key="test-key",
        base_url="https://model.invalid/v1",
        http_client=AsyncClient(transport=MockTransport(handler)),
        max_retries=0,
    )


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_investigation_passes_evidence_from_both_real_mcp_servers(self) -> None:
        calls = [
            ("telemetry__search_logs", {"service_name": "payments-api", "severity": "ERROR", "limit": 10}, "LOG-019"),
            ("telemetry__get_deployment_history", {"service_name": "payments-api", "window_hours": 24}, "pay-204"),
            ("telemetry__read_resource", {"uri": "service://runbooks/payments-api"}, "payments-oncall"),
            ("telemetry__read_resource", {"uri": "config://release-checklist"}, "Staging release checklist"),
            ("filesystem__read_text_file", {"path": "RELEASE_NOTES.md"}, "Promotion is blocked"),
            ("filesystem__read_text_file", {"path": "service-config.yaml"}, "minimum_gateway_timeout_ms: 500"),
        ]
        summary = "Payments release is blocked. The evidence points to the timeout change in pay-204."
        model_requests = 0

        def model(request: Request) -> Response:
            nonlocal model_requests
            self.assertEqual(request.url.path, "/v1/chat/completions")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "test-model")
            functions = {tool["function"]["name"]: tool["function"] for tool in body["tools"]}
            self.assertNotIn("telemetry__create_incident_ticket", functions)
            self.assertEqual(
                set(functions["telemetry__search_logs"]["parameters"]["required"]),
                {"service_name", "severity", "limit"},
            )
            self.assertIn(
                "service://runbooks/payments-api",
                functions["telemetry__read_resource"]["parameters"]["properties"]["uri"]["enum"],
            )
            messages = body["messages"]
            index = model_requests
            model_requests += 1
            self.assertIn("untrusted", messages[0]["content"])
            if index:
                result = messages[-1]
                self.assertEqual(result["tool_call_id"], f"call_{index - 1}")
                evidence = json.loads(result["content"])
                self.assertTrue(evidence["ok"])
                self.assertIn(calls[index - 1][2], json.dumps(evidence))
            if index == len(calls):
                return completion(summary=summary)
            name, arguments, _ = calls[index]
            return completion(tool_call(index, name, json.dumps(arguments)))

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "investigation.jsonl"
            async with model_client(model) as llm, connect_agent_tools() as tools:
                answer = await investigate(
                    "Why are payments failing, and is the release ready?",
                    llm, "test-model", tools, trace_path=trace,
                )
            events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(answer, summary)
        self.assertEqual(model_requests, len(calls) + 1)
        self.assertEqual([event["tool"] for event in events], [call[0] for call in calls])
        self.assertEqual([event["arguments"] for event in events], [call[1] for call in calls])
        self.assertTrue(all(event["status"] == "ok" and event["duration_ms"] >= 0 for event in events))
        self.assertEqual(len({event["run_id"] for event in events}), 1)

    async def test_invalid_denied_and_timed_out_calls_are_returned_to_the_model(self) -> None:
        tools = AgentTools()

        async def slow_tool(arguments: dict) -> dict:
            await asyncio.sleep(10)
            raise AssertionError("The timeout should prevent this line from running.")

        tools.register("slow_read", "A slow read-only operation.", {"type": "object"}, slow_tool)

        def model(request: Request) -> Response:
            messages = json.loads(request.content)["messages"]
            if messages[-1]["role"] == "user":
                return completion(
                    tool_call(0, "slow_read", "not JSON"),
                    tool_call(1, "telemetry__create_incident_ticket", "{}"),
                    tool_call(2, "slow_read", "{}"),
                )
            results = [json.loads(message["content"]) for message in messages if message["role"] == "tool"]
            self.assertEqual(len(results), 3)
            self.assertTrue(all(not result["ok"] for result in results))
            self.assertIn("unavailable", results[1]["error"])
            self.assertIn("timed out", results[2]["error"])
            return completion(summary="Some evidence was unavailable.")

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            async with model_client(model) as llm:
                answer = await investigate(
                    "Investigate a service.", llm, "test-model", tools,
                    trace_path=trace, tool_timeout=0.05,
                )
            statuses = [
                json.loads(line)["status"]
                for line in trace.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(answer, "Some evidence was unavailable.")
        self.assertEqual(statuses, ["error", "error", "timeout"])

    async def test_tool_budget_limits_batches_and_leaves_one_final_summary_turn(self) -> None:
        tools = AgentTools()
        calls = 0

        async def read_tool(arguments: dict) -> dict:
            nonlocal calls
            calls += 1
            return {"ok": True, "data": "observed"}

        tools.register("read_once", "Read evidence.", {"type": "object"}, read_tool)

        def model(request: Request) -> Response:
            body = json.loads(request.content)
            if "tools" in body:
                return completion(
                    tool_call(0, "read_once", "{}"), tool_call(1, "read_once", "{}"),
                )
            results = [message for message in body["messages"] if message["role"] == "tool"]
            self.assertEqual(len(results), 2)
            self.assertTrue(json.loads(results[0]["content"])["ok"])
            self.assertIn("exceeded", json.loads(results[1]["content"])["error"])
            return completion(summary="One check completed. Additional checks are outstanding.")

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            async with model_client(model) as llm:
                answer = await investigate(
                    "Check readiness.", llm, "test-model", tools, trace_path=trace, max_iterations=1,
                )
            self.assertEqual(len(trace.read_text(encoding="utf-8").splitlines()), 1)
        self.assertEqual(calls, 1)
        self.assertIn("outstanding", answer)


if __name__ == "__main__":
    unittest.main()
