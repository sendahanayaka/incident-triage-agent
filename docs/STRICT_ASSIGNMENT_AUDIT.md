# Strict Assignment Compliance & Codebase Audit Report

**Date:** 2026-11-25  
**Target:** Incident Triage & Release Readiness AI Agent with MCP  
**Scope:** Full-stack audit across Frontend, Backend, Agent Client, MCP Infrastructure, SQLite Schema, and LLM Provider Integrations.

---

## 1. Executive Summary

This audit assesses the codebase against the core assignment milestones:
- **Milestone 1:** Custom MCP Server (`ops-telemetry-mcp`) with required resources (`service://runbooks/{service_name}`, `config://release-checklist`) and tools (`search_logs`, `get_deployment_history`, `create_incident_ticket`).
- **Milestone 2:** Multi-Server Agent Orchestrator discovering capabilities from both `ops-telemetry-mcp` (Rust) and `filesystem` (Node.js) dynamically, supporting multi-step tool reasoning with execution guardrails.
- **Milestone 3:** Safety Guardrails (Human-in-the-Loop gate for state mutations, prompt injection defense, and automated evaluation suite).

The underlying MCP infrastructure (Rust server and Node filesystem server) is genuinely implemented and fully functional. However, **several critical workflow defects, hardcoded shortcuts, and approval triggers** were identified that undermine the dynamic behavior and cause false approval cards on normal queries.

---

## 2. Identified Defects & Compliance Audit

### Issue 1: Over-Aggressive Approval Triggers in Offline Transport
- **File:** `agent-client/llm_provider.py`
- **Location:** Line 620 in `create_offline_transport()`
- **Severity:** HIGH
- **Evidence:**
  ```python
  wants_ticket = any(k in norm_query for k in ("ticket", "propose", "remediate", "incident", "create ticket"))
  ```
- **Explanation:** The keyword `"incident"` was included in the condition that triggers `telemetry__create_incident_ticket`. Any prompt inquiring about an incident (e.g., *"Investigate critical payments-api incident and determine root cause"*) was falsely classified as a mutation request, forcing the agent to propose a ticket and create an unnecessary approval card.
- **Recommended Correction:** Remove `"incident"` and `"remediate"` from the trigger check. A ticket proposal must only be generated when the user explicitly requests one (e.g., `"propose ticket"`, `"create ticket"`, `"file ticket"`).

---

### Issue 2: Frontend Unconditionally Pulls Unrelated Pending Approvals
- **File:** `frontend/src/pages/InvestigationsPage.tsx`
- **Location:** Lines 49–61 in `handleSubmit()`
- **Severity:** HIGH
- **Evidence:**
  ```typescript
  const pending = await fetchPendingApprovals();
  const matched = pending.find((p) => ...);
  setPendingApprovals(matched ? [matched] : pending.slice(0, 1));
  ```
- **Explanation:** Whenever an investigation completes, the UI calls `fetchPendingApprovals()` and grabs either a loosely matched approval or **any arbitrary pending approval** from the database (`pending.slice(0, 1)`). Consequently, even purely read-only queries (e.g., inspecting log levels or deployment history) display an approval card if any pending approval exists in SQLite.
- **Recommended Correction:** The UI must ONLY display an approval card if the *current investigation run* actually invoked `telemetry__create_incident_ticket` with status `pending_approval`. If no mutation tool was called in the current run, `pendingApprovals` must remain empty.

---

### Issue 3: Fabricated Tool Call Fallback in Backend Agent
- **File:** `backend/app/orchestrator/agent.py`
- **Location:** Lines 247–330 in `execute_investigation()`
- **Severity:** MEDIUM
- **Evidence:**
  ```python
  if "payment" in norm_query:
      findings = "Investigation concluded: Payments API failure identified..."
      tool_calls = [
          ToolCallRecord(tool="telemetry__search_logs", arguments={...}, duration_ms=12.4),
          ToolCallRecord(tool="telemetry__get_deployment_history", arguments={...}, duration_ms=8.1),
      ]
  ```
- **Explanation:** If connecting to the MCP servers fails, the backend falls back to hardcoded regex strings and constructs artificial `ToolCallRecord` objects with fake durations (`12.4ms`, `8.1ms`), pretending tools were executed when they were not.
- **Recommended Correction:** Remove fabricated tool calls. If MCP servers cannot be reached, the investigation must fail cleanly or state that MCP tools were unreachable, rather than fabricating tool traces.

---

### Issue 4: Masked 429 Quota Exceeded Errors Under Nested ExceptionGroups
- **File:** `backend/app/orchestrator/agent.py` and `agent-client/orchestrator.py`
- **Location:** Line 162 in `execute_investigation()`, and line 242 in `investigate()`
- **Severity:** HIGH
- **Evidence:**
  ```text
  Live LLM investigation failed: ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  ```
- **Explanation:** In Python 3.11+, MCP's stdio client and AnyIO wrap subprocess async tasks in `ExceptionGroup`s. When Google's Gemini API rejected requests with HTTP 429 (`RESOURCE_EXHAUSTED: Generate content requests per day limit exceeded on Free Tier. Limit: 20`), the error was buried under 4 nested layers of `ExceptionGroup`, leaving the user with an unhelpful error message.
- **Recommended Correction:** Implement recursive unwrapping of `BaseExceptionGroup` down to the root exception. Detect HTTP 429 rate limits and quota exhaustion explicitly, and report the exact limitation with actionable remediation.

---

### Issue 5: Gemini Free-Tier Quota Exhaustion on Preview Models
- **File:** `.env` and `agent-client/llm_provider.py`
- **Location:** Google AI Studio Gemini API integration
- **Severity:** HIGH
- **Evidence:**
  Google API direct response:
  ```json
  {
    "error": {
      "code": 429,
      "message": "Generate content requests per day limit exceeded on Free Tier. Limit: 20, model: gemini-3-flash. Please retry in 23h.",
      "status": "RESOURCE_EXHAUSTED"
    }
  }
  ```
- **Explanation:** The user configured a free-tier Google Gemini API key. On Google AI Studio, experimental preview models (`gemini-3-flash-preview`) carry a strict quota of **20 requests per day per project**. Because an agentic ReAct loop makes 3–5 LLM requests per investigation (multi-turn reasoning), running 4–5 investigations completely consumes the daily quota.
- **Recommended Correction:** Document the free-tier quota constraints clearly. Allow seamless switching between `LLM_MODE=live` and `LLM_MODE=offline`. In offline mode, the system runs 100% locally with real MCP tools and zero API limits.

---

### Issue 6: Unnecessary / Dead Code for Unsupported Actions
- **File:** `backend/app/approvals/manager.py`
- **Location:** Lines 255–264 (`rollback_deployment`)
- **Severity:** LOW
- **Evidence:**
  ```python
  elif action_type == "rollback_deployment":
      execution_result = {"rollback_status": "initiated", ...}
  ```
- **Explanation:** `rollback_deployment` is not defined in the assignment specification or exposed as an MCP tool in `ops-telemetry-mcp`. The only assignment-defined protected mutation tool is `create_incident_ticket`.
- **Recommended Correction:** Scope approval execution strictly to assignment-defined mutation tools (`create_incident_ticket` / `telemetry__create_incident_ticket`).

---

### Issue 7: Multi-Turn Duplicate Ticket Creation Proposals
- **File:** `agent-client/orchestrator.py`
- **Location:** ReAct loop in `investigate()`
- **Severity:** MEDIUM
- **Evidence:**
  When `telemetry__create_incident_ticket` is called, `web_approval_callback` returns `status: "pending_approval"`. The ReAct loop sent this result back to the model without an explicit instruction to stop calling mutation tools, causing the model to re-attempt `create_incident_ticket` in subsequent iterations.
- **Recommended Correction:** Add an explicit orchestrator break or system message: when a mutation tool is submitted to the human approval gate, the agent must finalize its findings and conclude the investigation without re-invoking the mutation tool.

---

## 3. Next Steps & Corrective Plan

1. **Phase 2 (HITL Workflow):**
   - Fix `InvestigationsPage.tsx` so approval cards only appear when the *current run* invoked `telemetry__create_incident_ticket`.
   - Update `agent-client/llm_provider.py` so only explicit ticket requests trigger ticket proposals.
   - Prevent multi-turn duplicate ticket proposals in `orchestrator.py`.
2. **Phase 3 & 4 (Live LLM & Orchestration):**
   - Remove fake fallback tool records in `backend/app/orchestrator/agent.py`.
   - Ensure recursive exception unwrapping for clear quota/rate-limit diagnosis.
   - Refine system prompt to enforce read-only investigation by default.
3. **Phase 5 & 6 (UI & Testing):**
   - Verify all regression tests pass.
   - Test read-only investigation -> 0 approval cards.
   - Test ticket request -> exactly 1 approval card.
   - Test approval -> ticket written to SQLite `incident_tickets`.
   - Test rejection -> no ticket written to SQLite.
