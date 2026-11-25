"""Comprehensive test suite for Phase 14 & 15: OpenRouter-Ready LLM Provider & Offline Mode."""

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_CLIENT_DIR = str(REPO_ROOT / "agent-client")
if AGENT_CLIENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_CLIENT_DIR)

from llm_provider import (
    DEFAULT_LIVE_MODEL,
    DEFAULT_OFFLINE_MODEL,
    DEFAULT_OPENROUTER_BASE_URL,
    LLMConfig,
    create_offline_transport,
    get_llm_client,
    load_llm_config_from_env,
    validate_live_openrouter_config,
)


# ==============================================================================
# 1. Configuration Tests
# ==============================================================================

def test_default_offline_configuration():
    """Verify that by default, the agent runs in offline mode with zero network calls."""
    with patch.dict(os.environ, {}, clear=True):
        config = load_llm_config_from_env()
        assert config.provider == "offline"
        assert config.mode == "offline"
        assert config.model == DEFAULT_OFFLINE_MODEL
        assert not config.has_api_key
        assert config.is_offline is True
        assert config.is_live is False


def test_env_loading_openrouter_live():
    """Verify loading OpenRouter live configuration from environment variables."""
    custom_env = {
        "LLM_PROVIDER": "openrouter",
        "LLM_MODE": "live",
        "LLM_MODEL": "anthropic/claude-3.5-sonnet",
        "LLM_API_KEY": "sk-or-v1-mock-secret-key-12345",
        "LLM_BASE_URL": "https://openrouter.ai/api/v1",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        config = load_llm_config_from_env()
        assert config.provider == "openrouter"
        assert config.mode == "live"
        assert config.model == "anthropic/claude-3.5-sonnet"
        assert config.api_key == "sk-or-v1-mock-secret-key-12345"
        assert config.base_url == "https://openrouter.ai/api/v1"
        assert config.is_live is True
        assert config.is_offline is False
        assert config.has_api_key is True


def test_validate_live_openrouter_missing_key_raises():
    """Verify that attempting to activate live mode without an API key raises a clear ValueError."""
    config = LLMConfig(
        provider="openrouter",
        mode="live",
        model="anthropic/claude-3.5-sonnet",
        api_key="",
    )
    with pytest.raises(ValueError) as excinfo:
        validate_live_openrouter_config(config)
    assert "LLM_API_KEY is missing" in str(excinfo.value)
    assert "offline" in str(excinfo.value).lower()


def test_validate_live_openrouter_missing_model_raises():
    """Verify that live mode requires a non-empty model identifier."""
    config = LLMConfig(
        provider="openrouter",
        mode="live",
        model="",
        api_key="sk-or-valid-key",
    )
    with pytest.raises(ValueError) as excinfo:
        validate_live_openrouter_config(config)
    assert "LLM_MODEL is not set" in str(excinfo.value)


def test_safe_dict_never_exposes_secret_key():
    """Security check: verify that safe_dict() strips any secret api_key."""
    secret_key = "sk-or-v1-super-secret-production-key-do-not-leak"
    config = LLMConfig(
        provider="openrouter",
        mode="live",
        model="meta-llama/llama-3.3-70b-instruct",
        api_key=secret_key,
        base_url="https://openrouter.ai/api/v1",
    )
    safe = config.safe_dict()
    assert secret_key not in json.dumps(safe)
    assert safe["has_api_key"] is True
    assert "api_key" not in safe


# ==============================================================================
# 2. Endpoint Configuration Visibility Tests
# ==============================================================================

def test_health_endpoint_contains_safe_llm_status(client: TestClient):
    """Verify GET /api/health exposes LLM status without leaking secrets."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "llm" in data
    llm = data["llm"]
    assert "provider" in llm
    assert "mode" in llm
    assert "model" in llm
    assert "has_api_key" in llm
    assert "api_key" not in llm
    assert llm["mode"] in ("offline", "live")


def test_config_llm_endpoint(client: TestClient):
    """Verify dedicated GET /api/config/llm endpoint."""
    response = client.get("/api/config/llm")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] in ("offline", "openrouter", "gemini")
    assert "has_api_key" in data
    assert "api_key" not in data


# ==============================================================================
# 3. Offline Mode & Deterministic Mock Transport Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_offline_client_zero_network_request():
    """Verify get_llm_client in offline mode uses MockTransport and makes NO network calls."""
    config = LLMConfig(provider="offline", mode="offline")
    llm, model = get_llm_client(config)
    try:
        assert isinstance(llm, AsyncOpenAI)
        assert model == DEFAULT_OFFLINE_MODEL

        # Issue chat completion requesting a tool call
        messages: list[Any] = [
            {"role": "system", "content": "You are a triage agent."},
            {"role": "user", "content": "Investigate payments-api failure"},
        ]
        tools: list[Any] = [
            {
                "type": "function",
                "function": {
                    "name": "telemetry__search_logs",
                    "description": "Search logs",
                    "parameters": {"type": "object", "properties": {"service_name": {"type": "string"}}},
                },
            }
        ]

        response: Any = await llm.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=messages,
            tools=tools,
        )

        assert len(response.choices) > 0
        choice = response.choices[0]
        assert choice.message.tool_calls is not None
        assert len(choice.message.tool_calls) > 0
        assert choice.message.tool_calls[0].function.name == "telemetry__search_logs"
    finally:
        await llm.close()


@pytest.mark.asyncio
async def test_offline_client_synthesis_after_tool_response():
    """Verify offline mock transport provides final synthesized findings after tool response."""
    config = LLMConfig(provider="offline", mode="offline")
    llm, model = get_llm_client(config)
    try:
        messages: list[Any] = [
            {"role": "system", "content": "You are a triage agent."},
            {"role": "user", "content": "Investigate payments-api timeout"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "telemetry__search_logs", "arguments": '{"service_name":"payments-api"}'},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": json.dumps({"status": "ok", "logs": [{"id": "LOG-019", "message": "Downstream timeout"}]}),
            },
        ]

        response: Any = await llm.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=messages,
        )

        assert len(response.choices) > 0
        answer = response.choices[0].message.content
        assert answer is not None
        assert "payments" in answer.lower()
        assert "LOG-019" in answer
    finally:
        await llm.close()


# ==============================================================================
# 4. Mocked OpenRouter HTTP Request Tests (Testing live client pathway safely)
# ==============================================================================

@pytest.mark.asyncio
async def test_mocked_openrouter_live_flow():
    """Verify OpenRouter-configured AsyncOpenAI client correctly formats requests with Bearer auth."""
    called_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        called_requests.append(request)
        # Verify OpenRouter headers
        assert "Bearer test-openrouter-key" in request.headers.get("Authorization", "")
        # Return valid OpenAI/OpenRouter chat completion
        mock_body = {
            "id": "gen-12345",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Root cause identified: LOG-020 downstream timeout after deployment pay-204.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "anthropic/claude-3.5-sonnet",
        }
        return httpx.Response(200, json=mock_body)

    custom_transport = httpx.MockTransport(mock_handler)
    mock_http_client = httpx.AsyncClient(transport=custom_transport)

    config = LLMConfig(
        provider="openrouter",
        mode="live",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-openrouter-key",
        base_url="https://openrouter.ai/api/v1",
    )

    llm, model = get_llm_client(config, http_client=mock_http_client)
    try:
        user_msgs: list[Any] = [{"role": "user", "content": "What is the status?"}]
        res: Any = await llm.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=user_msgs,
        )
        assert len(called_requests) == 1
        assert "LOG-020" in (res.choices[0].message.content or "")
    finally:
        await llm.close()
        await mock_http_client.aclose()


@pytest.mark.asyncio
async def test_mocked_openrouter_401_unauthorized():
    """Verify OpenRouter 401 Unauthorized handling with mocked transport."""
    def mock_401_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API Key provided", "code": 401}})

    custom_transport = httpx.MockTransport(mock_401_handler)
    mock_http_client = httpx.AsyncClient(transport=custom_transport)

    config = LLMConfig(
        provider="openrouter",
        mode="live",
        model="anthropic/claude-3.5-sonnet",
        api_key="invalid-key",
    )

    llm, model = get_llm_client(config, http_client=mock_http_client)
    try:
        with pytest.raises(Exception):
            ping_msgs: list[Any] = [{"role": "user", "content": "Ping"}]
            await llm.chat.completions.create(  # type: ignore[call-overload]
                model=model,
                messages=ping_msgs,
            )
    finally:
        await llm.close()
        await mock_http_client.aclose()


@pytest.mark.asyncio
async def test_offline_notification_worker_investigation_and_ticket():
    """Verify offline mode handles notification-worker query with WARN logs, ticket proposal, and LOG-041."""
    config = LLMConfig(provider="offline", mode="offline")
    llm, model = get_llm_client(config)
    try:
        # Step 1: Initial tool selection
        msgs: list[Any] = [
            {"role": "user", "content": "Review notification-worker intermittent warnings and propose a critical incident ticket."}
        ]
        tools: list[Any] = [{"type": "function", "function": {"name": "telemetry__search_logs"}}]
        res1: Any = await llm.chat.completions.create(model=model, messages=msgs, tools=tools)  # type: ignore[call-overload]
        tcs = res1.choices[0].message.tool_calls
        assert tcs is not None
        assert len(tcs) == 2
        # Verify JSON arguments formatting and WARN severity
        log_call = next(tc for tc in tcs if tc.function.name == "telemetry__search_logs")
        log_args = json.loads(log_call.function.arguments)
        assert log_args["service_name"] == "notification-worker"
        assert log_args["severity"] == "WARN"

        # Step 2: Proposes ticket tailored to notification-worker
        msgs.append(res1.choices[0].message)
        msgs.append({"role": "tool", "tool_call_id": tcs[0].id, "content": json.dumps({"status": "ok"})})
        msgs.append({"role": "tool", "tool_call_id": tcs[1].id, "content": json.dumps({"status": "ok"})})
        res2: Any = await llm.chat.completions.create(model=model, messages=msgs, tools=tools)  # type: ignore[call-overload]
        tcs2 = res2.choices[0].message.tool_calls
        assert tcs2 is not None
        assert tcs2[0].function.name == "telemetry__create_incident_ticket"
        tkt_args = json.loads(tcs2[0].function.arguments)
        assert "notification" in tkt_args["title"].lower() or "notification" in tkt_args["assignee"].lower()
        assert tkt_args["severity"] == "CRITICAL"

        # Step 3: Synthesis citations include LOG-041 and notify-116
        msgs.append(res2.choices[0].message)
        msgs.append({"role": "tool", "tool_call_id": tcs2[0].id, "content": json.dumps({"status": "pending_approval"})})
        res3: Any = await llm.chat.completions.create(model=model, messages=msgs)  # type: ignore[call-overload]
        final_content = res3.choices[0].message.content or ""
        assert "LOG-041" in final_content
        assert "notify-116" in final_content
    finally:
        await llm.close()

