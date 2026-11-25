# Live LLM Integration & Debugging Report: Google Gemini API

**Date:** 2026-11-25  
**Target:** Google Gemini API Integration via OpenAI-Compatible Endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`)  
**Scope:** Model Compatibility, Authentication, Function/Tool Calling, Quota & Rate Limits, Exception Handling  

---

## 1. Architecture Overview

The agent orchestrator supports two modes of execution:
1. **Strict Offline Mode (`LLM_MODE=offline`):** Deterministic ReAct loop executing against real MCP servers via an in-memory HTTP mock transport. Unlimited, zero-cost, fully reproducible.
2. **Live LLM Mode (`LLM_MODE=live`):** Connects to an external OpenAI-compatible API endpoint using `AsyncOpenAI`. When configured with Google Gemini (`LLM_PROVIDER=gemini`), it connects to `https://generativelanguage.googleapis.com/v1beta/openai/`.

---

## 2. Root Cause Analysis: Why Gemini Live Mode Failed

When the user configured their Google Gemini API key (`LLM_API_KEY=AQ.Ab8RN6...`), the agent encountered failure states with the following root causes:

### Root Cause 1: Free-Tier Per-Day Quota Exhaustion
- **Inspection Method:** Raw HTTP payload analysis directly against Google's API endpoint.
- **Evidence from Google:**
  ```json
  {
    "error": {
      "code": 429,
      "message": "Generate content requests per day limit exceeded on Free Tier. Limit: 20, model: gemini-3-flash. Please retry in 23h.",
      "status": "RESOURCE_EXHAUSTED",
      "details": [
        {
          "@type": "type.googleapis.com/google.rpc.QuotaFailure",
          "violations": [
            {
              "description": "Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.",
              "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
              "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
              "quotaValue": "20"
            }
          ]
        }
      ]
    }
  }
  ```
- **Explanation:** Google AI Studio enforces a hard daily limit of **20 requests per day per project** on experimental/preview models (`gemini-3-flash`). Because an agentic ReAct loop issues 3–5 tool calls per investigation, 4 investigations consumed the entire daily quota.

---

### Root Cause 2: Model Naming & Deprecation on Google API
- **Attempted Model:** `gemini-2.5-flash`
- **Evidence from Google:**
  ```json
  {
    "error": {
      "code": 404,
      "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features..."
    }
  }
  ```
- **Attempted Model:** `gemini-3.8-flash`
- **Evidence from Google:**
  ```json
  {
    "error": {
      "code": 503,
      "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.",
      "status": "UNAVAILABLE"
    }
  }
  ```
- **Explanation:** Google's model catalog deprecates older preview aliases and experiences high server load on newer flash models. The model supported on the user's project is `gemini-3-flash-preview`.

---

### Root Cause 3: Python 3.11+ AnyIO Nested ExceptionGroup Masking
- **Symptom:** UI displayed `Live LLM investigation failed: ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)`.
- **Explanation:** MCP clients run subprocess stdio sessions managed by `anyio.create_task_group()`. When the LLM client raised `openai.RateLimitError (HTTP 429)`, AnyIO wrapped the exception in an `ExceptionGroup`. Because stdio transport and session management also use task groups, the exception was wrapped 4 layers deep:
  `ExceptionGroup -> ExceptionGroup -> ExceptionGroup -> ExceptionGroup -> RateLimitError: 429`.
- **Fix:** Implemented `_extract_root_cause(exc)` in `agent.py` to recursively unwrap nested `BaseExceptionGroup` instances down to the leaf error and surface the exact Google quota violation with clear remediation instructions.

---

## 3. Tool Calling Verification with Live Gemini

Before the free daily quota of 20 requests was reached, the live Gemini model was directly verified executing tools through the ReAct loop:

```powershell
Model: gemini-3-flash-preview
Endpoint: https://generativelanguage.googleapis.com/v1beta/openai/
Tool Definitions:
  - telemetry__search_logs: {"service_name": "payments-api", "severity": "ERROR", "limit": 5}
  - telemetry__get_deployment_history: {"service_name": "payments-api", "window_hours": 24}
  - telemetry__read_resource: {"uri": "service://runbooks/payments-api"}
```

Gemini generated valid OpenAI-format tool calls, the orchestrator dispatched them to the Rust MCP server, and Gemini successfully synthesized findings from the returned logs (`LOG-019`, `LOG-020`, `pay-204`).

---

## 4. Operational Recommendations for Live Mode

1. **For Production Testing:**
   - Link a Google Cloud billing account to Google AI Studio to unlock standard Pay-As-You-Go quotas (1,000 RPM, unlimited daily requests), OR
   - Use an OpenRouter API key (`LLM_PROVIDER=openrouter`, `LLM_MODEL=anthropic/claude-3.5-sonnet` or `google/gemini-2.0-flash-001`).
2. **For Zero-Cost Unlimited Development:**
   - Keep `LLM_MODE=offline` in `.env`. This bypasses external rate limits while running genuine tool loops against the real Rust MCP server and SQLite database.
