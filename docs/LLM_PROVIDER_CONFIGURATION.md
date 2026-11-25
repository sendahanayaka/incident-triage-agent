# LLM Provider Configuration & OpenRouter Integration Guide

This guide describes the dual-mode LLM architecture of the **Incident Triage & Release Readiness Agent**:
1. **Deterministic Offline Mode (Default):** Runs complete multi-step investigations, MCP tool calls, HITL ticket proposals, and execution tracing with zero external network traffic and no API keys required.
2. **OpenRouter Live Mode:** Connects to OpenRouter's OpenAI-compatible API to execute reasoning with state-of-the-art frontier models through configuration alone, requiring zero application code modifications.

---

## 1. Quick Start: Mode Comparison

| Mode | `LLM_MODE` | `LLM_PROVIDER` | `LLM_API_KEY` | Network Calls | Cost | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Offline Mode** *(Default)* | `offline` | `offline` | Not required | **0 (Local in-memory)** | **$0.00** | Local development, CI/CD, manual testing, evaluation benchmark |
| **OpenRouter Live Mode** | `live` | `openrouter` | Required (`sk-or-v1-...`) | Outbound to OpenRouter | Per token | Production deployment, real LLM reasoning |

---

## 2. Environment Variables Specification

All LLM provider behaviors are controlled via standard environment variables defined in your `.env` file at the repository root.

| Environment Variable | Default Value | Description | Required in Live Mode? |
| :--- | :--- | :--- | :--- |
| `LLM_PROVIDER` | `offline` | Primary LLM provider identifier (`offline` or `openrouter`). | Yes (`openrouter`) |
| `LLM_MODE` | `offline` | Execution mode (`offline` or `live`). | Yes (`live`) |
| `LLM_MODEL` | `offline/incident-triage-v1` | Model identifier string. | Yes (e.g., `anthropic/claude-3.5-sonnet`) |
| `LLM_API_KEY` | *(None)* | OpenRouter API authentication key. | Yes |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter OpenAI-compatible API base URL. | Optional (defaults to OpenRouter v1) |
| `LLM_TIMEOUT_SECONDS` | `60` | HTTP request timeout in seconds. | Optional |
| `LLM_MAX_RETRIES` | `2` | Number of automatic retries on transient network errors. | Optional |

---

## 3. How to Activate OpenRouter Live Mode (Zero Code Modifications)

When your supervisor or administrator provides an OpenRouter API key, follow these exact steps to activate live mode:

### Step 1: Open `.env`
Open the `.env` file in the root of the project directory.

### Step 2: Configure Live Settings
Set the following values:

```env
# ==============================================================================
# LLM Provider Configuration (OpenRouter Live Mode)
# ==============================================================================
LLM_PROVIDER=openrouter
LLM_MODE=live
LLM_MODEL=anthropic/claude-3.5-sonnet
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
```

### Step 3: Restart Backend Service
Restart the FastAPI backend process:
```powershell
# Stop current server (Ctrl+C), then restart:
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: Verify in Frontend Dashboard
1. Open the web interface at `http://localhost:5173`.
2. Look at the top navigation bar: the LLM status pill will switch from `LLM: OFFLINE (offline)` to `LLM: LIVE (openrouter)`.
3. The Runtime Status banner will show:
   - **Mode:** `LIVE`
   - **Provider:** `openrouter`
   - **Active Model:** `anthropic/claude-3.5-sonnet`
   - **API Key:** `Configured (Live Ready)`

**Notice:** No Python, TypeScript, or React code needs to be edited or recompiled.

---

## 4. Recommended Models on OpenRouter

The agent utilizes standard OpenAI function calling schemas (`tools`). We recommend the following tested models for operational triage:

| Model Identifier | Provider | Tool Calling Quality | Cost Efficiency | Context Window | Recommended For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `anthropic/claude-3.5-sonnet` | Anthropic | Exceptional | High | 200k tokens | **Default recommended:** Best reasoning and tool calling accuracy |
| `openai/gpt-4o` | OpenAI | Exceptional | High | 128k tokens | High reasoning capability, fast response |
| `meta-llama/llama-3.3-70b-instruct` | Meta / Open Source | Strong | Very High (Low cost) | 128k tokens | Cost-effective open weights option |
| `google/gemini-flash-1.5` | Google | Strong | Maximum (Lowest cost) | 1M tokens | Rapid triage over large log outputs |

---

## 5. Offline Deterministic Mode Details

In offline mode (`LLM_MODE=offline`):
- The agent client configures an in-memory `httpx.MockTransport`.
- No outbound HTTP sockets or network requests are created.
- The transport intercepts requests sent to `http://offline.local/v1/chat/completions`.
- It dynamically inspects the user query, determines appropriate tool definitions, generates standard OpenAI tool call structures (`telemetry__search_logs`, `telemetry__get_deployment_history`, `telemetry__read_resource`, `filesystem__read_text_file`, `telemetry__create_incident_ticket`), and parses tool responses to generate synthesized markdown findings with valid evidence citations.
- Full Human-in-the-Loop (HITL) ticket proposals and approval gates function identically to live mode.

---

## 6. Security & Credential Hygiene

1. **Zero Secret Leakage:** The application enforces strict secret hygiene:
   - Secret API keys are never exposed in `/api/health` or `/api/config/llm`. Only `has_api_key: boolean` is returned.
   - Secret keys are never serialized to JSONL traces, log files, or terminal stdout.
   - The `.env` file is excluded in `.gitignore`.
2. **Missing Key Guard:** If `LLM_MODE=live` is configured without an API key, the backend raises an explicit, descriptive `ValueError` directing the operator to either provide the key or switch back to `LLM_MODE=offline`.
