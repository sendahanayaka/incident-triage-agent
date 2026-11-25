# Comprehensive Test Cases: OpenRouter Architecture & Offline Mode

This document catalogs the test cases for the Incident Triage & Release Readiness Agent across configuration, offline execution, mocked OpenRouter live requests, HITL safety gates, and regression suites.

---

## 1. Test Suite Classification Matrix

| Category | Test File | Scope | Requires Network? | Requires API Key? |
| :--- | :--- | :--- | :--- | :--- |
| **LLM Configuration** | `backend/tests/test_llm_provider.py` | Environment loading, validation, safe dict | **No** | **No** |
| **Offline Mode** | `backend/tests/test_llm_provider.py` | In-memory MockTransport, ReAct tool calls | **No** | **No** |
| **Mocked OpenRouter** | `backend/tests/test_llm_provider.py` | Live AsyncOpenAI request formation, 401 handling | **No** | **No (Mocked)** |
| **FastAPI Backend** | `backend/tests/` (10 files) | Endpoints, DB persistence, validation | **No** | **No** |
| **Agent Core & HITL** | `agent-client/tests/` (3 files) | ReAct loop, tool budget, approval callbacks | **No** | **No** |
| **Evaluation Benchmark** | `evaluation/tests/` | 8 Benchmark triage scenarios | **No** | **No** |
| **Frontend UI** | `frontend/src/tests/` (6 files) | React views, navigation, modals, approvals | **No** | **No** |

---

## 2. Detailed Test Cases

### TC-CFG-01: Default Configuration Fallback
- **Description:** Verifies that when no `.env` or environment variables are provided, the system defaults to safe offline mode.
- **Input:** Empty environment dictionary.
- **Expected Outcome:** `provider == "offline"`, `mode == "offline"`, `model == "offline/incident-triage-v1"`, `has_api_key == False`, `is_offline == True`.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-CFG-02: OpenRouter Live Configuration Loading
- **Description:** Verifies that specifying OpenRouter variables correctly loads live configuration.
- **Input:** `LLM_PROVIDER=openrouter`, `LLM_MODE=live`, `LLM_API_KEY=sk-or-v1-xxx`, `LLM_MODEL=anthropic/claude-3.5-sonnet`.
- **Expected Outcome:** `is_live == True`, `has_api_key == True`, `model == "anthropic/claude-3.5-sonnet"`.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-CFG-03: Missing Key Live Validation Rejection
- **Description:** Verifies that enabling live mode without an API key is blocked with a clear `ValueError`.
- **Input:** `LLM_MODE=live`, `LLM_API_KEY=""`.
- **Expected Outcome:** `ValueError` raised containing `"LLM_API_KEY is missing"`, directing operator to `.env`.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-CFG-04: Credential Hygiene & Sanitization
- **Description:** Verifies that `.safe_dict()` and API responses never expose the secret API key.
- **Input:** `LLMConfig` initialized with secret key `"sk-or-v1-super-secret-key"`.
- **Expected Outcome:** Secret key string absent from serialized dictionary; only `has_api_key: True` boolean is present.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-OFF-01: Zero Network Socket Execution
- **Description:** Verifies that `get_llm_client()` in offline mode uses `httpx.MockTransport` and executes without network access.
- **Input:** User query: `"Investigate payments-api failure"`.
- **Expected Outcome:** Response generated containing tool call `telemetry__search_logs` with zero socket operations.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-OFF-02: Multi-Turn ReAct Synthesis
- **Description:** Verifies that after receiving tool response logs, offline mode synthesizes markdown root cause findings with citations.
- **Input:** History containing tool response with `LOG-019` downstream timeout.
- **Expected Outcome:** Model returns content citing `LOG-019` and explaining root cause.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-MOCK-01: OpenRouter Bearer Authorization Formation
- **Description:** Verifies that live client transmits HTTP `Authorization: Bearer <key>` header to OpenRouter endpoint.
- **Input:** Mock transport intercepting outbound request.
- **Expected Outcome:** Outbound request contains expected Bearer header and OpenRouter attribution headers.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-MOCK-02: OpenRouter 401 Unauthorized Handling
- **Description:** Verifies graceful error propagation when OpenRouter rejects invalid credentials.
- **Input:** Mock transport returning HTTP 401 with JSON error payload.
- **Expected Outcome:** AsyncOpenAI raises `AuthenticationError` / HTTP status exception cleanly.
- **Status:** PASS (Automated in `test_llm_provider.py`).

### TC-HITL-01: Ticket Creation Authorization Approval
- **Description:** Verifies that mutation action `telemetry__create_incident_ticket` requests approval and executes when approved.
- **Input:** Approval callback returning `True`.
- **Expected Outcome:** Ticket generated and persisted in SQLite; trace event records `approval_decision: "approved"`.
- **Status:** PASS (Automated in `agent-client/tests/test_hitl.py`).

### TC-HITL-02: Ticket Creation Authorization Rejection
- **Description:** Verifies that when human rejects mutation proposal, tool execution is blocked.
- **Input:** Approval callback returning `False`.
- **Expected Outcome:** Tool returns rejection message; no ticket persisted; trace event records `approval_decision: "rejected"`.
- **Status:** PASS (Automated in `agent-client/tests/test_hitl.py`).

### TC-UI-01: Runtime Status Banner Rendering
- **Description:** Verifies frontend displays active provider, mode, model, and key status.
- **Input:** Render `DashboardPage` with backend health data.
- **Expected Outcome:** Element `data-testid="llm-runtime-status-card"` rendered with mode pill.
- **Status:** PASS (Automated in `frontend/src/tests/Dashboard.test.tsx`).

---

## 3. How to Run All Test Suites

Execute the following commands in order:

```powershell
# 1. Backend & LLM Provider Test Suite (40 tests)
.\.venv\Scripts\python.exe -m pytest backend/tests

# 2. Agent Client Core & HITL Test Suite (20 tests)
.\.venv\Scripts\python.exe -m pytest "agent-client/tests" -o pythonpath="agent-client ."

# 3. Evaluation Benchmark & Trace Validation (17 tests + 4 traces)
.\.venv\Scripts\python.exe -m pytest evaluation/tests
.\.venv\Scripts\python.exe evaluation/validate_traces.py

# 4. Frontend Component Test Suite (9 tests)
cd frontend
npx vitest run
npm run build
```
