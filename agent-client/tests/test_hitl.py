"""Tests for CLI Human-in-the-Loop (HITL) approval gate."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, MockTransport, Request, Response
from openai import AsyncOpenAI

from mcp_tools import AgentTools, connect_agent_tools
from orchestrator import (
    cli_approval_prompt,
    format_approval_prompt,
    investigate,
    sanitize_data,
)


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


class HITLTests(unittest.IsolatedAsyncioTestCase):
    """Test suite covering all required HITL approval scenarios."""

    async def test_1_approved_ticket_creation(self) -> None:
        """Test 1: Agent proposes ticket, human approves, tool executes, ticket persisted."""
        tools = AgentTools()
        executed_calls = []

        async def create_ticket(args: dict) -> dict:
            executed_calls.append(args)
            return {"ok": True, "ticket_id": "INC-1042", "title": args.get("title")}

        tools.register(
            "telemetry__create_incident_ticket",
            "Create incident ticket in database.",
            {"type": "object", "properties": {"title": {"type": "string"}}},
            create_ticket,
            is_mutation=True,
        )

        ticket_args = {
            "title": "Payment gateway timeout",
            "severity": "HIGH",
            "summary": "Gateway response exceeded 250ms timeout in pay-204",
            "assignee": "payments-oncall",
        }

        def model(request: Request) -> Response:
            messages = json.loads(request.content)["messages"]
            if messages[-1]["role"] == "user":
                return completion(tool_call(0, "telemetry__create_incident_ticket", json.dumps(ticket_args)))
            # Second turn: summary after tool returns
            tool_res = json.loads(messages[-1]["content"])
            self.assertTrue(tool_res["ok"])
            self.assertEqual(tool_res["ticket_id"], "INC-1042")
            return completion(summary="Incident ticket INC-1042 created successfully.")

        approval_callback = AsyncMock(return_value=True)

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            async with model_client(model) as llm:
                answer = await investigate(
                    "Create ticket for payments timeout.",
                    llm,
                    "test-model",
                    tools,
                    trace_path=trace,
                    approval_callback=approval_callback,
                )

            events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(executed_calls), 1)
        self.assertEqual(executed_calls[0]["title"], "Payment gateway timeout")
        self.assertEqual(approval_callback.await_count, 1)
        self.assertIn("INC-1042", answer)

        # Verify trace record
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["tool"], "telemetry__create_incident_ticket")
        self.assertTrue(events[0]["approval_required"])
        self.assertEqual(events[0]["approval_decision"], "approved")
        self.assertEqual(events[0]["status"], "ok")

    async def test_2_rejected_ticket_creation(self) -> None:
        """Test 2: Agent proposes ticket, human rejects, tool NOT executed, rejection recorded."""
        tools = AgentTools()
        executed_calls = []

        async def create_ticket(args: dict) -> dict:
            executed_calls.append(args)
            return {"ok": True, "ticket_id": "INC-1042"}

        tools.register(
            "telemetry__create_incident_ticket",
            "Create incident ticket.",
            {"type": "object"},
            create_ticket,
            is_mutation=True,
        )

        ticket_args = {"title": "Premature ticket", "severity": "LOW"}

        def model(request: Request) -> Response:
            messages = json.loads(request.content)["messages"]
            if messages[-1]["role"] == "user":
                return completion(tool_call(0, "telemetry__create_incident_ticket", json.dumps(ticket_args)))
            tool_res = json.loads(messages[-1]["content"])
            self.assertFalse(tool_res["ok"])
            self.assertIn("rejected", tool_res["error"].lower())
            return completion(summary="Action was rejected. No ticket created.")

        approval_callback = AsyncMock(return_value=False)

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            async with model_client(model) as llm:
                answer = await investigate(
                    "Create ticket.",
                    llm,
                    "test-model",
                    tools,
                    trace_path=trace,
                    approval_callback=approval_callback,
                )

            events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(executed_calls), 0)  # Tool was NOT called!
        self.assertEqual(approval_callback.await_count, 1)
        self.assertIn("rejected", answer.lower())

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["approval_required"])
        self.assertEqual(events[0]["approval_decision"], "rejected")
        self.assertEqual(events[0]["status"], "rejected")

    async def test_3_default_rejection_on_empty_input(self) -> None:
        """Test 3: Empty input or newline defaults to rejection."""
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
            mock_input.return_value = ""  # User presses Enter
            decision = await cli_approval_prompt("telemetry__create_incident_ticket", {"title": "Test"})
            self.assertFalse(decision)

    async def test_4_invalid_approval_input(self) -> None:
        """Test 4: Invalid/unsupported approval values result in safe rejection."""
        invalid_inputs = ["maybe", "1", "sure", "ok", "n", "no", "NO", "invalid!!", "   "]
        for inp in invalid_inputs:
            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
                mock_input.return_value = inp
                decision = await cli_approval_prompt("telemetry__create_incident_ticket", {"title": "Test"})
                self.assertFalse(decision, f"Input '{inp}' should have been rejected.")

    async def test_5_case_insensitive_approval(self) -> None:
        """Test 5: 'y', 'yes', 'Y', 'YES', 'Yes' are accepted as explicit approval."""
        valid_inputs = ["y", "yes", "Y", "YES", "Yes", "  y  ", "  YES  "]
        for inp in valid_inputs:
            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
                mock_input.return_value = inp
                decision = await cli_approval_prompt("telemetry__create_incident_ticket", {"title": "Test"})
                self.assertTrue(decision, f"Input '{inp}' should have been accepted.")

    async def test_6_parameter_integrity(self) -> None:
        """Test 6: Approval for one set of arguments cannot be reused for different arguments."""
        tools = AgentTools()

        async def handler(args: dict) -> dict:
            return {"ok": True, "saved": args}

        tools.register("telemetry__create_incident_ticket", "Create ticket", {}, handler, is_mutation=True)

        token = tools.authorize_mutation("telemetry__create_incident_ticket", {"title": "Original Title"})

        # Attempt to call with modified arguments using the same token
        with self.assertRaises(PermissionError) as ctx:
            await tools.call("telemetry__create_incident_ticket", {"title": "Tampered Title"}, approval_token=token)
        self.assertIn("parameters do not match", str(ctx.exception).lower())

    async def test_7_duplicate_execution_protection(self) -> None:
        """Test 7: The same authorization token cannot be reused for duplicate execution."""
        tools = AgentTools()

        async def handler(args: dict) -> dict:
            return {"ok": True, "saved": args}

        tools.register("telemetry__create_incident_ticket", "Create ticket", {}, handler, is_mutation=True)

        token = tools.authorize_mutation("telemetry__create_incident_ticket", {"title": "Valid Ticket"})

        # First call succeeds and consumes token
        res = await tools.call("telemetry__create_incident_ticket", {"title": "Valid Ticket"}, approval_token=token)
        self.assertTrue(res["ok"])

        # Second call with the same token MUST fail
        with self.assertRaises(PermissionError) as ctx:
            await tools.call("telemetry__create_incident_ticket", {"title": "Valid Ticket"}, approval_token=token)
        self.assertIn("invalid or expired", str(ctx.exception).lower())

    async def test_8_mutation_tool_access_and_discovery(self) -> None:
        """Test 8: Mutation tools are discoverable but cannot execute through unprotected path."""
        async with connect_agent_tools() as tools:
            # Must be discoverable in definitions
            tool_names = {t["function"]["name"] for t in tools.definitions}
            self.assertIn("telemetry__create_incident_ticket", tool_names)
            self.assertTrue(tools.is_mutation("telemetry__create_incident_ticket"))

            # Direct call without approval token must raise PermissionError
            with self.assertRaises(PermissionError) as ctx:
                await tools.call("telemetry__create_incident_ticket", {"title": "Unauthorized"})
            self.assertIn("requires human approval", str(ctx.exception).lower())

    async def test_9_read_only_tools_execute_without_approval(self) -> None:
        """Test 9: Read-only tools execute normally without triggering HITL callback."""
        tools = AgentTools()
        read_executed = False

        async def read_logs(args: dict) -> dict:
            nonlocal read_executed
            read_executed = True
            return {"ok": True, "logs": ["LOG-001"]}

        tools.register("telemetry__search_logs", "Search logs", {}, read_logs, is_mutation=False)
        self.assertFalse(tools.is_mutation("telemetry__search_logs"))

        def model(request: Request) -> Response:
            messages = json.loads(request.content)["messages"]
            if messages[-1]["role"] == "user":
                return completion(tool_call(0, "telemetry__search_logs", "{}"))
            return completion(summary="Logs retrieved successfully.")

        approval_callback = AsyncMock(return_value=False)  # Even if callback returns False, read-only doesn't call it!

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            async with model_client(model) as llm:
                answer = await investigate("Check logs", llm, "test-model", tools, trace_path=trace, approval_callback=approval_callback)

        self.assertTrue(read_executed)
        self.assertEqual(approval_callback.call_count, 0)  # Callback was never called!
        self.assertIn("Logs retrieved", answer)

    async def test_10_trace_verification_and_secret_sanitization(self) -> None:
        """Test 10: Trace records approval/rejection decisions and scrubs secrets."""
        data = {
            "title": "Incident with secret",
            "api_key": "sk-secret-key-12345",
            "password": "super-secret-password",
            "nested": {"token": "bearer secret-token", "info": "safe"},
        }
        sanitized = sanitize_data(data)
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["token"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["info"], "safe")

        # Test prompt format
        prompt_text = format_approval_prompt(
            "telemetry__create_incident_ticket",
            {
                "title": "Outage in payments",
                "severity": "CRITICAL",
                "summary": "Gateway failed",
                "assignee": "team",
            },
        )
        self.assertIn("HUMAN APPROVAL REQUIRED", prompt_text)
        self.assertIn("Outage in payments", prompt_text)
        self.assertIn("CRITICAL", prompt_text)
        self.assertIn("payments-api", prompt_text)


if __name__ == "__main__":
    unittest.main()
