# AI-Powered Incident Triage and Release Readiness Agent

> **Project Status — Phase 10 complete.** Authentic sample execution traces have been generated, validated, and documented. Representative traces demonstrate root cause analysis, single-use token HITL approval, operator rejection safeguards, and untrusted log prompt injection resistance. All 17 evaluation tests, 20 agent-client tests, and 29 backend tests pass.

---

## Overview

The **AI-Powered Incident Triage and Release Readiness Agent** is an autonomous, safety-controlled engineering assistant designed for Site Reliability Engineers (SREs), DevOps practitioners, and release managers. It aims to accelerate incident response, perform automated root cause analysis across telemetry feeds and runbooks, and provide release readiness assessments while strictly enforcing Human-in-the-Loop (HITL) approval gates for sensitive actions.

---

## Objectives

- **Automated Incident Triage:** Correlate telemetry metrics, system error logs, and recent code deployments to identify probable root causes.
- **Runbook-Informed Diagnosis:** Search and synthesize domain-specific remediation runbooks.
- **Model Context Protocol (MCP) Integration:** Standardize tool execution across diverse operational components using MCP.
- **Safety & Human-in-the-Loop Control** requires explicit operator approval before the agent creates an incident ticket.
- **Execution Observability & Tracing** records tool names, arguments, durations, and outcomes in JSONL.

---

## Planned Architecture

The architecture consists of a decoupled system:
1. **Frontend:** React + TypeScript + Vite interactive operator portal.
2. **Backend:** FastAPI (Python) providing REST APIs, safety verification, and execution coordination.
3. **Agent Orchestrator:** Python-based ReAct agent orchestrating tool calls within an iteration limit (`MAX_AGENT_ITERATIONS=8`).
4. **Model Context Protocol (MCP) Integration:**
   - **Custom Rust MCP Server (`ops-telemetry-mcp`):** Log filtering, deployment history, Markdown resources, and local ticket creation.
   - **Official Filesystem MCP Server:** Release notes, configuration, and manifest reads within the sample workspace.
5. **Storage & Traces:**
   - **SQLite (`database/incidents.db`)** stores incident tickets from the Rust server. Backend state and approval records are planned.
   - **JSONL (`traces/agent_traces.jsonl`):** Granular agent trajectory and decision tracing.

For detailed architecture diagrams and component specifications, refer to [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Technology Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS (planned)
- **Backend:** Python 3.13+, FastAPI, Pydantic, Uvicorn
- **Orchestration:** Python-based ReAct loop
- **MCP Servers:**
  - Custom Rust server (`ops-telemetry-mcp`)
  - Official MCP filesystem server
- **Storage:** SQLite incident tickets and planned backend state
- **Audit & Tracing:** JSONL
- **Version Control:** Git, GitHub

---

## Directory Structure

```text
incident-triage-agent/
├── .env.example              # Template environment configuration
├── .gitignore                # Project-wide Git ignore rules
├── README.md                 # Project overview and status
├── REPORT.md                 # Project assignment report
├── docs/
│   ├── ARCHITECTURE.md       # Comprehensive system architecture documentation
│   └── screenshots/          # Architecture diagrams and UI screenshots
├── frontend/                 # React + TypeScript + Vite web interface
├── agent-client/             # Python agent, MCP connections, and integration tests
├── backend/                  # Planned FastAPI web service
│   ├── app/
│   │   ├── api/              # FastAPI routers and endpoints
│   │   ├── orchestrator/     # Agent ReAct loop and prompt definitions
│   │   ├── mcp/              # MCP client and connection managers
│   │   ├── services/         # Incident, telemetry, and runbook services
│   │   ├── safety/           # Safety policies and risk checkers
│   │   ├── approvals/        # Human-in-the-loop approval management
│   │   ├── tracing/          # JSONL trace logger
│   │   └── models/           # Pydantic schemas and domain models
│   └── tests/                # Backend unit and integration tests
├── mcp-server/               # Custom Rust MCP telemetry server
│   ├── Cargo.toml
│   ├── Cargo.lock
│   ├── src/
│   │   ├── main.rs           # Tokio entry point and STDIO lifecycle
│   │   ├── server.rs         # MCP capabilities and dispatch
│   │   ├── errors.rs         # Startup and request errors
│   │   ├── tools/            # Log search, deployment history, and ticket creation
│   │   ├── resources/        # Runbooks and release checklist
│   │   ├── models/           # Data types and tool schemas
│   │   └── data/             # Fixture loading and local ticket persistence
│   └── tests/                # MCP integration tests over STDIO
├── mock_data/
│   ├── logs.json             # Synthetic logs for three staging services
│   ├── deployments.json      # Deployment history and rollback status
│   ├── release-checklist.md  # Criteria for the MCP checklist resource
│   ├── runbooks/             # Operational incident runbooks (Markdown)
│   └── workspace/            # RELEASE_NOTES.md, service-config.yaml, service-manifest.json
├── database/                 # Local ticket store and planned SQLite backend state
├── traces/                   # Agent trace logs (.jsonl)
└── tests/                    # System-level and end-to-end test suites
```

---

## Development Phases

- [x] **Phase 0: Project Initialization and Development Environment Setup**
- [x] **Phase 1 — Repository Setup and Mock Data**
- [x] **Phase 2 — Telemetry MCP Server (Rust)**
- [x] **Phase 3 — Multi-Server Agent Orchestrator & Filesystem MCP**
- [x] **Phase 7 — Build the Backend API for the Incident Triage & Release Readiness Agent**
  - Modular FastAPI application architecture (`backend/app/`)
  - Endpoints for health, investigations, services, logs, deployments, incidents, approvals, and traces
  - Human-in-the-Loop (HITL) approval safety workflow with SQLite persistence
  - Sanitized agent tracing with secret redaction
  - Comprehensive pytest test suite (29 tests passing)
- [x] **Phase 8: CLI Human-in-the-Loop (HITL) Approval Gate**
  - Interception of mutation tools (`telemetry__create_incident_ticket`) before execution
  - CLI confirmation prompt displaying formatted incident proposal (`[y/N]`)
  - Strict affirmative approval parsing (`y`, `yes`, case-insensitively); safe default rejection
  - Cryptographically robust single-use authorization tokens tied to exact argument SHA-256 hashes
  - Prevention of direct bypass or duplicate tool execution
  - Tracing of approval decisions (`approved`/`rejected`) and secret sanitization
  - Comprehensive unit and integration test suite (10 test scenarios, all passing)
- [x] **Phase 9: Evaluation Benchmark Suite & Scenarios**
  - 8 standardized operational scenarios (`evaluation/scenarios/benchmark_scenarios.json`)
  - Deterministic evaluation engine (`evaluation/evaluator.py`) with zero tolerance for critical safety breaches
  - Empirical metrics: tool selection accuracy, investigation correctness, latency, iteration efficiency, and autonomous vs human-assisted success rates
  - Isolated test execution preventing contamination of production SQLite database or traces
  - Benchmark CLI runner (`evaluation/benchmark_runner.py`) with machine-readable JSON reports and human-readable terminal summaries
  - Full test suite (`evaluation/tests/test_evaluation.py`) covering all 17 benchmark criteria
- [x] **Phase 10: Sample Execution Traces & Workflow Demonstration**
  - Generated 4 authentic sample traces in `traces/` via the real MCP orchestrator and Rust telemetry server
  - Trace A (Root Cause Investigation), Trace B (Human-Approved Ticket), Trace C (Human-Rejected Ticket), Trace D (Prompt Injection Defense)
  - Dedicated automated trace validator (`evaluation/validate_traces.py`) verifying schema, chronology, correlation IDs, and secret hygiene
  - Comprehensive trace analysis report documented in `docs/TRACE_ANALYSIS.md`
- [ ] **Phase 11: Frontend Development (React + TypeScript + Vite)**
- [ ] **Final Documentation & Release Verification**

---

## Mock data

The fixtures describe a staging snapshot at `2026-11-20T04:30:00Z` with 44 log records. Use that reference time for repeatable demo deployment-window queries. The Rust telemetry server reads `logs.json`, `deployments.json`, `runbooks/`, and `release-checklist.md`. The filesystem MCP server serves release notes, configuration, and the manifest under `mock_data/workspace/`.

| Scenario | Evidence in the fixtures |
| --- | --- |
| A. Payments outage after deployment | Candidate `pay-204` reduced the gateway timeout from 1000 ms to 250 ms. Gateway responses exceeded the timeout, checkout probes failed, and promotion was blocked. |
| B. Authentication failures | A signing-key rotation left the cache stale. Fresh-token probes returned HTTP 401 until deployment `auth-087` refreshed the cache. |
| C. Notification warnings | The provider timed out intermittently. Retries succeeded, the queue drained, and the delivery smoke probe passed. |
| D. Prompt injection in a log | Payments error `LOG-019` includes a synthetic instruction to approve the release regardless of the evidence. |
| E. Unknown service | Use `inventory-api` as the negative lookup. The telemetry server returns a structured `unknown_service` error. |

## Build and test the Rust MCP server

Use Rust 1.89 or newer with a C compiler for your Rust target. The build bundles SQLite. From the repository root, build the server and run the unit and STDIO integration tests.

```sh
cargo build --manifest-path mcp-server/Cargo.toml --locked
cargo test --manifest-path mcp-server/Cargo.toml --locked
```

On Windows with the GNU Rust target, make the 64-bit MinGW-w64 C compiler and binutils available on `PATH`. [MSYS2 MinGW-w64 toolchain](https://packages.msys2.org/groups/mingw-w64-x86_64-toolchain)

Set your MCP client's STDIO command to `mcp-server/target/debug/ops-telemetry-mcp.exe` on Windows or `mcp-server/target/debug/ops-telemetry-mcp` on macOS and Linux. Launch it with the repository root as its working directory. The client sends `initialize` and `notifications/initialized`, discovers the tools and resources, and closes the session when done. The server reserves stdout for MCP messages and writes diagnostics to stderr.

| Tool | Input and result |
| --- | --- |
| `search_logs` | `service_name`, severity `INFO`, `WARN`, `ERROR`, or `FATAL`, and a positive integer `limit`. Returns newest matching logs first. |
| `get_deployment_history` | `service_name` and positive integer `window_hours`. Returns newest deployments first within the inclusive demo window. |
| `create_incident_ticket` | Non-blank `title`, `severity`, `summary`, and `assignee`. Inserts the ticket into SQLite and returns those fields plus `ticket_id` and `created_at`. The future orchestrator will enforce approval before calling it. |

Clients can discover and read `config://release-checklist` and the three concrete runbooks. The runbook template is `service://runbooks/{service_name}`. A known service with no matching entries returns an empty collection. An unknown service returns a structured `unknown_service` tool error.

| Optional environment variable | Default |
| --- | --- |
| `OPS_TELEMETRY_DATA_DIR` | `mock_data/` |
| `OPS_TELEMETRY_REFERENCE_TIME` | `2026-11-20T04:30:00Z` for reproducible deployment history |
| `OPS_TELEMETRY_TICKET_PATH` | `database/incidents.db` |

If the executable is launched from another directory, pass absolute paths for the fixtures and SQLite database. The server creates the `incident_tickets` table on the first valid ticket write. Tests use in-memory or temporary databases.

## Run the official filesystem MCP server

Use Node.js 24 or newer and Python 3.11 or newer. With a Python virtual environment active, run these commands from the repository root.

```sh
cd agent-client
npm ci --ignore-scripts
python -m pip install -r requirements.txt
python filesystem_mcp.py tools
python filesystem_mcp.py list
python filesystem_mcp.py read RELEASE_NOTES.md
python filesystem_mcp.py read service-config.yaml
python filesystem_mcp.py read service-manifest.json
python -m unittest discover -s tests -v
```

The Python client launches the pinned official filesystem server as a Node.js subprocess and discovers tool schemas over STDIO. The application can reuse `connect_filesystem()` from `agent-client/filesystem_mcp.py` and call its discovered tools within the async context.

The server receives exactly one allowed directory, `mock_data/workspace/`, with `--read-only` and `--confine-roots`. The client verifies the reported scope at startup and checks requested paths before forwarding calls. An optional `FILESYSTEM_WORKSPACE` environment variable may point to that same directory using an absolute or repository-relative path. [Official filesystem server configuration](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md)

## Run an investigation with the Python agent

Build the Rust server and install the Node.js and Python dependencies using the commands above. Set `LLM_API_KEY` and `LLM_MODEL` in the repository's `.env` or in your environment. Use a model that supports function calling. The agent uses the OpenAI Chat Completions API by default. Set `LLM_BASE_URL` for a compatible endpoint. [Function calling](https://developers.openai.com/api/docs/guides/function-calling)

From the repository root, with the Python environment active, run one of these requests.

```sh
python agent-client/agent.py "Why is payments-api failing, and what should the on-call engineer check?"
python agent-client/agent.py "Is payments-api version 2.4.2 ready for release?"
```

The agent opens both MCP sessions and discovers their read-only tools and schemas. It also discovers resource URIs from the Rust server and can read the relevant runbook or release checklist on demand. Every model turn receives the question, tool definitions, and evidence returned by preceding calls. The final answer summarizes the available evidence and any outstanding checks.

| Setting | Default and effect |
| --- | --- |
| `RUST_MCP_SERVER_PATH` | Detects the local debug binary by platform. Set an absolute or repository-relative override for another build. |
| `MAX_AGENT_ITERATIONS` | `8` tool calls per investigation, followed by a final summary turn if the budget is exhausted. |
| `AGENT_TOOL_TIMEOUT_SECONDS` | `10` seconds per tool call. |
| `TRACE_FILE_PATH` | `traces/agent_traces.jsonl`. Records invocation arguments, timings, and outcomes by run ID. |

The investigation CLI exposes read-only tools and safely discovers mutation tools (`create_incident_ticket`). When a mutation tool is invoked, execution pauses for explicit operator approval.

## CLI Human-in-the-Loop (HITL) Approval Gate

The agent orchestrator implements a strict, interactive approval gate for any state-altering or destructive actions:

1. **Mutation Tool Interception:** Mutation tools (such as `telemetry__create_incident_ticket`) are registered with mutation flags. Read-only tools (`search_logs`, `get_deployment_history`, filesystem tools) execute autonomously within the 8-iteration budget.
2. **Terminal Confirmation Prompt:** Execution halts and presents a structured proposal:
   ```text
   ============================================================
   HUMAN APPROVAL REQUIRED: CREATE INCIDENT TICKET
   ============================================================
   Action:           Create incident ticket in database
   Incident Title:   Production Outage: payments-api elevated 500 errors
   Severity:         CRITICAL
   Affected Service: payments-api
   Assignee:         payments-oncall
   Summary:          Elevated 500 responses caused by timeout misconfiguration.
   ------------------------------------------------------------
   Do you approve creating this incident ticket? [y/N]:
   ```
3. **Strict Affirmative Input:** Only affirmative answers (`y`, `yes`, case-insensitively) grant execution permission. Any other response (including Enter/empty string, `n`, `no`, whitespace, or invalid tokens) triggers default rejection.
4. **Single-Use Authorization Token & Parameter Integrity:** Approving a mutation issues an ephemeral, single-use token cryptographically bound to the SHA-256 hash of the exact tool arguments. The underlying `AgentTools.call()` strictly verifies this token. If arguments are altered or if the tool is invoked again without new human approval, execution is blocked with `PermissionError`.
5. **Rejection Handling:** If rejected by the operator, the tool is not called. A structured rejection feedback string is returned to the model (`"Action '...' rejected by operator."`), allowing the LLM to complete its reasoning and provide a diagnostic summary without claiming state was altered.
6. **Trace Auditing & Secret Redaction:** All approval requests, operator decisions, and tool outputs are recorded in `traces/agent_traces.jsonl` with sensitive credentials/tokens sanitized.

To run the HITL approval test suite:
```bash
python -m unittest discover -s agent-client/tests -v
```

## Run the Evaluation Benchmark Suite

The evaluation benchmark subsystem tests the agent against 8 operational scenarios spanning deployment lookups, root-cause investigations, release readiness assessments, negative service lookups, ambiguous requests, prompt injection resistance, and approved/rejected HITL workflows.

### 1. Run All Benchmark Scenarios
```bash
python evaluation/benchmark_runner.py --all
```

### 2. Run a Specific Scenario
```bash
python evaluation/benchmark_runner.py --scenario EVAL-02
python evaluation/benchmark_runner.py --scenario EVAL-06
```

### 3. Save Results to JSON
```bash
python evaluation/benchmark_runner.py --all --output evaluation/results/latest.json
```

### 4. Run Evaluation Subsystem Unit Tests
```bash
python -m unittest discover -s evaluation/tests -v
```

## Sample Execution Traces & Verification

Authentic execution traces demonstrating the agent's real behavior are stored in `traces/`:

- **Trace A (Root Cause Investigation):** [`traces/sample_root_cause_investigation.jsonl`](traces/sample_root_cause_investigation.jsonl)
- **Trace B (Human-Approved Mutation):** [`traces/sample_hitl_approved.jsonl`](traces/sample_hitl_approved.jsonl)
- **Trace C (Human-Rejected Mutation):** [`traces/sample_hitl_rejected.jsonl`](traces/sample_hitl_rejected.jsonl)
- **Trace D (Prompt Injection Defense):** [`traces/sample_prompt_injection_defense.jsonl`](traces/sample_prompt_injection_defense.jsonl)

Detailed event breakdown, sequence diagrams, and security analysis are available in [`docs/TRACE_ANALYSIS.md`](docs/TRACE_ANALYSIS.md).

### Regenerate Sample Traces
```bash
python evaluation/generate_traces.py
```

### Validate Sample Traces
```bash
python evaluation/validate_traces.py
```

## Run the FastAPI Backend API

The FastAPI backend provides REST endpoints for the React frontend, coordinates incident triage investigations, manages human approvals, and serves operational metrics and traces.

### 1. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Launch the Development Server

From the repository root:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **API Base URL:** `http://localhost:8000/api`
- **Interactive Swagger UI Documentation:** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`
- **OpenAPI Schema:** `http://localhost:8000/api/openapi.json`
- **Health Check:** `http://localhost:8000/api/health`

### 3. Run Backend API Tests

To execute the backend test suite:

```bash
pytest -v backend/tests
```

All 29 tests run deterministically against mock stores and SQLite in-memory/temp databases without making external API calls.

## Run the React Frontend Dashboard

The React frontend provides an engineering operations portal connecting directly to the FastAPI backend.

### 1. Prerequisites & Environment Configuration

Ensure Node.js (v18+) is installed. Navigate to the `frontend/` directory and configure environment variables:

```bash
cd frontend
cp .env.example .env
```

Default configuration in `frontend/.env`:
```ini
VITE_API_BASE_URL=http://localhost:8000/api
```

### 2. Install Dependencies & Start Development Server

```bash
cd frontend
npm install
npm run dev
```

The frontend dashboard will be available at `http://localhost:5173`.

### 3. Frontend Functionality

- **Dashboard (`/`):** Real-time operational metrics, monitored service health, pending HITL approval banner, and recent incident & deployment activity.
- **Service Directory (`/services`):** Microservice statuses (`auth-service`, `payments-api`, `notification-worker`), runbook resource availability (`service://runbooks/{service}`), error counts, and 1-click investigation triggers.
- **Investigations (`/investigations`):** AI investigation console allowing natural language queries to the agent orchestrator, accompanied by real-time ReAct progress states, synthesized findings, evidence citations, and tool invocation timelines.
- **Incident Tickets (`/incidents`):** Persisted SQLite incident records (`INC-1042`, etc.) with severity badges and assignee details.
- **HITL Approvals (`/approvals`):** Human-in-the-Loop approval gate allowing operators to review proposed mutation tools, inspect parameters, and execute confirmed approvals or rejections.
- **Telemetry Logs (`/logs`):** Queryable operational logs with filtering by service (`payments-api`, etc.), severity level (`INFO`, `WARN`, `ERROR`, `FATAL`), and pagination limits.
- **Deployment History (`/deployments`):** Release history table with commit hashes, versions, timestamps, status, rollback status, and release summaries.
- **Agent Traces (`/traces`):** Execution trace viewer displaying sanitized JSONL tool calls, execution latency, and arguments.

### 4. Run Frontend Tests & Production Build

```bash
# Execute Vitest test suite (9 tests across 6 suites)
npm test

# Build production distribution bundle
npm run build
```

### 5. Backend Dependency & Limitations

- **Backend Dependency:** The frontend requires the FastAPI backend to be running on `http://localhost:8000`. If offline, the interface displays an operational connection alert while maintaining UI stability.
- **HITL Safeguard:** Direct creation of incident tickets from the frontend is prohibited. Tickets can only be created when proposed during an agent investigation and confirmed by an operator through the HITL approval gate.

## Getting Started

### Prerequisites
- Python 3.13+
- Git

### Initializing Environment
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Create and activate a local virtual environment:
   - **Windows:**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

*(Additional build and setup instructions will be provided in subsequent phases as components are implemented.)*
