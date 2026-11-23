# System Architecture Documentation

**Project Name:** AI-Powered Incident Triage and Release Readiness Agent  
**Document Version:** 0.8.0 (Phase 8 CLI HITL Approval Gate Implemented)  
**Status:** Implemented CLI & Backend Core / Planned Frontend Baseline

---

## 1. Project Overview

The **AI-Powered Incident Triage and Release Readiness Agent** is an enterprise-grade agentic system designed to assist site reliability engineers (SREs), DevOps engineers, and release managers. Modern cloud services generate immense volumes of telemetry data (metrics, logs, traces, alerts), making root cause identification, triage, and release sign-offs time-consuming, cognitive bottlenecks.

This project delivers an autonomous, safety-gated AI agent that:
- Ingests telemetry, incident alerts, and operational runbooks.
- Correlates telemetry anomalies with recent deployment commits and configurations.
- Interacts with standardized external systems and tools using the **Model Context Protocol (MCP)**.
- Recommends mitigation steps and requires **Human-in-the-Loop (HITL)** approval before the agent creates an incident ticket.
- Provides end-to-end auditability and execution tracing.

> **Phase 3 status.** The Python CLI orchestrator discovers and queries both MCP servers and communicates with a configurable model API. The approval flow, web API, and UI are planned.

---

## 2. System Architecture

The overall system follows a decoupled, layered micro-architecture comprising an interactive Web frontend, an orchestration backend service, two MCP servers (a high-performance custom Rust MCP server and an official MCP filesystem server), persistent storage, and an audit tracing pipeline.

```
+-------------------------------------------------------------------------+
|                           User / SRE Operator                           |
+-------------------------------------------------------------------------+
                                    |
                                    v (HTTP / WebSocket)
+-------------------------------------------------------------------------+
|                         React + Vite Frontend                           |
|  - Incident Dashboard         - Live Agent Trace Viewer                 |
|  - HITL Approval Modal        - Telemetry & Release Readiness Views     |
+-------------------------------------------------------------------------+
                                    |
                                    v (REST API / Async Events)
+-------------------------------------------------------------------------+
|                       FastAPI Backend Service                           |
|  - API Routing & Endpoints    - Safety Gating & Policy Engine           |
|  - HITL Approvals Manager     - JSONL Audit Trace Recorder              |
+-------------------------------------------------------------------------+
                                    |
                                    v (In-Process)
+-------------------------------------------------------------------------+
|                       Agent Orchestrator (Python)                       |
|  - ReAct / Plan-and-Solve Loop - Context & Memory Management            |
|  - Tool Call Dispatcher        - Iteration Limiter (Max 8 Iterations)   |
+-------------------------------------------------------------------------+
                |                                           |
                v (Stdio JSON-RPC via MCP)                  v (Stdio JSON-RPC via MCP)
+---------------------------------------+   +---------------------------------------+
|        Custom Rust MCP Server         |   |     Official MCP Filesystem Server    |
|       (ops-telemetry-mcp)             |   |           (@modelcontextprotocol)     |
|  - Runbooks and release checklist     |   |  - Release notes inspection           |
|  - Log filtering                      |   |  - Configuration workspace browsing   |
|  - Deployment status checks           |   |                                       |
|  - Local incident ticket creation     |   |                                       |
+---------------------------------------+   +---------------------------------------+
                |                                           |
                +---------------------+---------------------+
                                      |
                                      v
                        +---------------------------+
                        |  Mock Telemetry / Data    |
                        |  - mock_data/runbooks/    |
                        |  - mock_data/workspace/   |
                        +---------------------------+

Persistent Stores:
- SQLite database: database/incidents.db (Incident tickets and planned backend state)
- Trace Store: traces/agent_traces.jsonl (Step-by-step LLM decisions, tool inputs/outputs)
```

---

## 3. React Frontend Responsibilities (Planned)

The frontend is built with **React**, **TypeScript**, and **Vite** (with Tailwind CSS styling):
- **Incident Dashboard:** Real-time visibility into active incidents, severity classifications, and assigned priorities.
- **Triage & Release Readiness Views:** Consolidated interface displaying system health scores, deployment statuses, and release risk indicators.
- **Interactive Trace Visualizer:** Real-time stream of the agent's reasoning steps, tool discovery queries, and MCP tool invocations.
- **Human-in-the-Loop (HITL) Action Portal:** Interactive approval modals where human operators inspect proposed remediation actions (parameters, risks, rollbacks), then explicitly approve or reject them.

---

## 4. FastAPI Backend Responsibilities (Implemented in Phase 7)

The backend is developed in **Python** using **FastAPI**, structured into a clean, modular service architecture:

```text
backend/
├── requirements.txt
├── app/
│   ├── main.py                  # FastAPI application, CORS, and global exception handlers
│   ├── core/
│   │   ├── config.py            # Pydantic Settings, environment and dynamic path resolution
│   ├── api/
│   │   ├── dependencies.py      # Dependency injection providers for services
│   │   └── routes/              # Modular API route controllers
│   │       ├── health.py        # GET /api/health
│   │       ├── investigations.py# POST /api/investigations, GET /api/investigations/{id}
│   │       ├── services.py      # GET /api/services
│   │       ├── logs.py          # GET /api/logs
│   │       ├── deployments.py   # GET /api/deployments
│   │       ├── incidents.py     # GET /api/incidents
│   │       ├── approvals.py     # GET /api/approvals/pending, POST /approve, POST /reject
│   │       └── traces.py        # GET /api/traces
│   ├── models/                  # Pydantic request and response schemas
│   ├── services/                # Business logic and data coordination layer
│   ├── orchestrator/            # Integration bridge to Python agent orchestrator
│   ├── mcp/                     # Integration bridge to MCP client connections
│   ├── safety/                  # Action risk classification and guardrails
│   ├── approvals/               # SQLite approval workflow manager
│   └── tracing/                 # Sanitized trace log loader with secret redaction
└── tests/                       # Complete pytest suite with 29 test cases
```

### 4.1 REST API Endpoints

| HTTP Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check returning status and application metadata |
| `POST` | `/api/investigations` | Start AI-powered incident triage or release readiness investigation |
| `GET` | `/api/investigations/{id}` | Retrieve investigation findings, citations, and tool call history |
| `GET` | `/api/services` | Retrieve simulated operational services, status, and health metrics |
| `GET` | `/api/logs` | Query logs with optional service, severity, and limit filters |
| `GET` | `/api/deployments` | Retrieve deployment history with optional service filter |
| `GET` | `/api/incidents` | Retrieve persisted incident tickets from SQLite (`database/incidents.db`) |
| `GET` | `/api/approvals/pending` | Retrieve pending human-in-the-loop action proposals |
| `POST` | `/api/approvals/{id}/approve` | Approve and execute a pending mutating action |
| `POST` | `/api/approvals/{id}/reject` | Reject a pending action, preventing execution |
| `GET` | `/api/traces` | Retrieve sanitized agent execution traces scrubbed of secrets |
| `GET` | `/` | Root discovery endpoint |

### 4.2 Cross-Origin Resource Sharing (CORS)
CORS is configured via FastAPI's `CORSMiddleware`, allowing connections from frontend origins:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:3000`

### 4.3 Error Handling and Sanitization
- `HTTPException` returns standardized `{"detail": ...}` payloads.
- `RequestValidationError` returns HTTP 422 with validation errors.
- `ValueError` returns HTTP 400 Bad Request.
- Unhandled internal exceptions return HTTP 500 without leaking stack traces or credentials to clients.
- Traces automatically redact API keys, tokens, and authorization headers before transmission.

---

## 5. Agent Orchestrator Responsibilities

The CLI starts the orchestrator with a user question and a Chat Completions client. The orchestrator discovers the read-only tool schemas from each MCP server, names tools by server, and exposes discovered telemetry resources for on-demand reads. Each structured tool request is dispatched over MCP and its result is returned to the model under the same call ID.

The loop applies a configurable tool-call budget and a timeout per call. The JSONL trace records the requested tool, arguments, duration, and outcome. Operator approval and execution of protected writes are planned.

---

## 6. MCP Client Responsibilities (Planned)

The Python backend implements an MCP client complying with the **Model Context Protocol**:
- **Connection Management:** Spawns and manages sub-processes for stdio-based MCP servers.
- **Dynamic Tool Discovery:** Queries servers (`tools/list`) at startup to register available capabilities and schemas dynamically.
- **Resource reads** use `resources/read` for runbooks and the release checklist.
- **Standardized Execution:** Translates orchestrator tool calls into JSON-RPC requests, handling timeouts, validation, and error serialization.

---

## 7. Custom Rust MCP Server Responsibilities

`ops-telemetry-mcp` loads JSON and Markdown fixtures at startup. The official Rust MCP SDK negotiates the session over STDIO, advertises capabilities, and dispatches requests to Rust handlers.

- `search_logs` filters seeded logs by service and severity.
- `get_deployment_history` filters deployments using the configured demo clock.
- `create_incident_ticket` inserts a row into SQLite inside a transaction and returns the saved record. Its tool metadata identifies it as a write. The orchestrator will enforce approval before invoking it.
- The release checklist and per-service runbooks are exposed as read-only Markdown resources.

---

## 8. Official Filesystem MCP Server

The Python client launches the official Node.js server with the repository's `mock_data/workspace/` directory as its only allowed root. The server runs in read-only mode and confines legacy MCP Roots to that directory. The application verifies the active directory and exposes the discovered `list_allowed_directories`, `list_directory`, and `read_text_file` tools. File reads use the official server over STDIO.

---

## 9. SQLite Responsibilities

The Rust server initializes the `incident_tickets` table in `database/incidents.db` when it saves the first ticket. It stores the ticket fields and creation time and derives the public incident ID from the generated row ID. Ticket writes use transactions to preserve consistency across concurrent calls.

Planned backend storage includes the following.

- **Incident State** tracks root-cause hypotheses and resolution status.
- **Approval Records:** Complete ledger of human approval requests, timestamps, operator decisions, and justification notes.
- **Audit Logging:** Historical records linking incident triage sessions with their corresponding trace files.

---

## 10. Mock Data Structure

To ensure repeatable evaluations, deterministic testing, and safe demonstration without connecting to live cloud environments:
- `mock_data/logs.json` and `mock_data/deployments.json`: Synthetic telemetry for three staging services, including a payments outage correlated with a recent deployment.
- `mock_data/runbooks/` and `mock_data/release-checklist.md`: Read-only resources for the custom telemetry server.
- `mock_data/workspace/`: Release notes, service configuration, and a service manifest for the filesystem server.

---

## 11. Agent Tracing and Observability (Planned)

Full observability through **JSONL** event logging (`traces/agent_traces.jsonl`):
- **Structured Events:** Every step records timestamp, iteration index, prompt metadata, LLM reasoning thoughts, raw tool calls, tool responses, and safety approvals.
- **Replayability:** Enables benchmark replays, offline evaluation of reasoning quality, and failure mode analysis.
- **Zero Secret Exposure:** Strict scrubbing of credentials and sensitive payloads before trace emission.

---

## 12. Planned Agent Workflow

```
[Incident Alert]
       |
       v
[1. Ingest Alert & Parse Symptoms]
       |
       v
[2. Discover Tools via MCP Client]
       |
       v
[3. Query Telemetry (Rust MCP: logs, metrics)] <----+
       |                                            |
       v                                            | (Iterate <= 8)
[4. Inspect Runbooks & Configs (Filesystem MCP)]    |
       |                                            |
       v                                            |
[5. Synthesize Root Cause Hypothesis] --------------+
       |
       +--> [Is Remediation Action Safe/Read-Only?]
                 |                        |
             (Yes)                       (No - Mutation Required)
                 |                        |
                 |                        v
                 |           [Pause: Request Human Approval]
                 |                        |
                 |                  +-----+-----+
                 |                  |           |
                 |             (Approved)   (Rejected)
                 |                  |           |
                 +------------------+           v
                 |                        [Adjust Plan]
                 v
[6. Execute Tool / Finalize Diagnosis]
       |
       v
[7. Produce Triage Report & Release Readiness Assessment]
```

---

## 13. Human-in-the-Loop Approval Workflow

Safety is a core architectural invariant. Destructive or state-altering actions cannot execute autonomously under any circumstance.

### 13.1 Tool Risk Classification
Every MCP tool is statically or dynamically tagged with a risk classification:
- **Read-Only Tools:** `search_logs`, `get_deployment_history`, filesystem inspection tools (`read_text_file`, `list_directory`), and resource queries (`service://runbooks/{service_name}`, `config://release-checklist`). These execute autonomously within the 8-iteration limit.
- **Mutation Tools:** `create_incident_ticket` (`telemetry__create_incident_ticket`). Modifies persistent system state (SQLite `incident_tickets` table).

### 13.2 CLI Approval Workflow (Implemented in Phase 8)
1. **Tool Discovery:** The orchestrator discovers `create_incident_ticket` alongside read-only tools, registering it with `is_mutation=True`.
2. **Execution Interception:** When the model emits a tool call for `create_incident_ticket`, `orchestrator._execute_tool()` intercepts the call before dispatching to the underlying MCP client.
3. **Interactive Terminal Prompt:** Execution yields control to an asynchronous approval callback (`cli_approval_prompt`), which displays the ticket action, title, severity, affected service, assignee, and summary.
4. **Strict Approval Parsing:**
   - Evaluates input case-insensitively against `{"y", "yes"}`.
   - Any other input (including Enter / empty line, EOF, `n`, `no`, or unknown input) defaults immediately to rejection (`approved=False`).
5. **Single-Use Authorization Token:**
   - On approval, the orchestrator requests an ephemeral authorization token via `tools.authorize_mutation(tool_name, arguments)`.
   - The token is cryptographically tied to the SHA-256 hash of the exact canonical JSON representation of `arguments`.
   - `AgentTools.call(name, arguments, approval_token=token)` validates that the token exists, matches the exact arguments, and is consumed (deleted) immediately upon execution.
   - Any bypass attempt or direct invocation without a valid, unspent token raises `PermissionError`.
6. **Operator Rejection Flow:**
   - If rejected, the MCP tool is never invoked.
   - A descriptive rejection error is injected back into the LLM conversation context: `Action 'telemetry__create_incident_ticket' was rejected by the operator.`
   - The LLM receives this result and continues its diagnostic loop, summarizing root-cause findings without falsely asserting that an incident ticket was created.
7. **Trace Logging:** Trace events capture `approval_required: true`, `approval_decision: "approved" | "rejected"`, timestamp, and sanitized arguments/results.

### 13.3 Web Backend Approval Workflow (Implemented in Phase 7)
For the web-based React dashboard, the FastAPI backend implements an equivalent asynchronous approval manager (`backend/app/approvals/manager.py`):
- Pends approval requests in SQLite (`approvals` table).
- Surfaces pending approvals via `GET /api/approvals/pending`.
- Accepts decisions via `POST /api/approvals/{approval_id}/decision` (`APPROVED` or `REJECTED`) with operator identity and justification notes.

---

## 14. Safety and Security Considerations

- **Strict Sandbox Boundaries:** Filesystem MCP server is bound exclusively to `mock_data/workspace/`.
- **Iteration Safeguard:** Hard limit of 8 iterations prevents infinite loops and uncontrolled LLM execution costs.
- **Credential Protection:** Secrets are never hardcoded. Environment files (`.env`) are strictly ignored by Git.
- **Input Validation:** Backend uses Pydantic schemas to validate all payloads, parameters, and MCP tool responses.
- **Audit Trails:** Immutable trace logs preserve exact inputs, decisions, and outputs for compliance.

---

## 15. Planned Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Operator UI, triage dashboards, HITL portal |
| **Backend** | Python 3.13+, FastAPI, Pydantic, Uvicorn | REST API, safety policies, session management |
| **Orchestration** | Python custom ReAct orchestrator | Agent reasoning loop, context management |
| **Protocol** | Model Context Protocol (MCP) | Standardized tool and resource interfacing |
| **Telemetry MCP Server** | Rust, Tokio, `rmcp` / JSON-RPC | High-throughput telemetry and ops tooling |
| **Filesystem MCP Server** | Official Node.js MCP Filesystem Server | Read-only access to the release workspace |
| **Database** | SQLite 3 | Incident records, state tracking, HITL requests |
| **Tracing** | JSON Lines (JSONL) | Granular agent execution traces and benchmarks |
| **Testing** | Pytest (Python), Cargo Test (Rust), Vitest (React) | Comprehensive multi-tier test suites |

---

## 16. Evaluation Strategy (Planned)

The project will be evaluated across distinct qualitative and quantitative dimensions:
1. **Triage Accuracy:** Percentage of incidents correctly diagnosed against ground truth root causes.
2. **Tool Selection Efficiency:** Number of tool calls required to reach root cause (optimizing within the 8-iteration budget).
3. **Safety Enforcement:** Verification that 100% of mutation tool calls trigger human approval gates without bypass.
4. **Latency & Overhead:** End-to-end response times and MCP communication overhead.
5. **Observability Completeness:** Full reconstruction fidelity of agent reasoning paths via `agent_traces.jsonl`.
