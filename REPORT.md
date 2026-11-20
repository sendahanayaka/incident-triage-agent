# Project Report: AI-Powered Incident Triage and Release Readiness Agent

**Course / Module:** Software Engineering Assignment 2  
**Author:** Sendahanayaka  
**Repository:** https://github.com/sendahanayaka/incident-triage-agent  
**Status:** Phase 3 complete

---

## 1. Introduction

In modern cloud computing environments, distributed microservices continuously generate vast amounts of observability data, including logs, metrics, traces, and alert streams. When an incident occurs, Site Reliability Engineers (SREs) and on-call developers face high cognitive loads under strict Mean-Time-to-Detect (MTTD) and Mean-Time-to-Resolve (MTTR) constraints. This project presents an AI-driven, safety-gated autonomous agent capable of triaging incidents, assessing release readiness, querying multi-source operational data through the Model Context Protocol (MCP), and executing remediation actions under explicit human supervision.

---

## 2. Problem Statement

Incident diagnosis in complex architectures presents several fundamental challenges:
1. **Telemetry Overload:** Correlating disparate logs and metric spikes across distributed microservices requires significant manual effort.
2. **Context Disconnection:** Diagnostic runbooks and deployment manifests often reside in different repositories or documentation wikis, slowing down context retrieval.
3. **Safety Risks in Autonomous Remediation:** Fully autonomous remediation agents risk executing destructive actions (such as premature rollbacks or unintended service terminations) without human operator oversight.
4. **Tool Fragmentation:** Traditional operational tools lack a unified protocol for agentic discovery and structured execution.

---

## 3. Objectives

- **Standardized Tooling:** Utilize the Model Context Protocol (MCP) to decouple LLM reasoning from tool implementation across Rust-based telemetry services and file systems.
- **Cognitive Loop with Hard Safety Bounds:** Implement a ReAct orchestration engine constrained to a maximum of 8 iterations to guarantee termination and bounded cost.
- **Human-in-the-Loop (HITL) Safety:** Enforce mandatory human approval checkpoints for all state-mutating and remediation actions.
- **Observability and auditing** record tool calls, arguments, durations, and outcomes.
- **Usable Operator Interface:** Provide a reactive web dashboard built with React and FastAPI to visualize agent reasoning, incidents, and approvals.

---

## 4. Proposed Solution

The solution introduces a multi-tier agent architecture:
- A **Rust MCP server** for filtering fixture logs, looking up deployments, serving operational guidance, and creating local incident tickets.
- An **Official Filesystem MCP server** for reading release notes and configuration within the sample workspace.
- A **Python FastAPI backend** with an embedded ReAct orchestrator and safety gating layer.
- A **React + Vite frontend** delivering real-time incident monitoring, trace inspection, and HITL decision management.
- A **Structured JSONL Tracing system** providing auditability and evaluation metrics.

---

## 5. System Architecture

*(Planned architectural design. Detailed specifications and diagrams are maintained in `docs/ARCHITECTURE.md`.)*

The system integrates three primary tiers:
1. **Presentation Tier:** React + TypeScript + Vite web interface for operators.
2. **Application & Orchestration Tier:** FastAPI REST service managing sessions, safety gating, SQLite persistence, and the Python ReAct agent loop.
3. **Protocol & Tool Tier:** MCP servers interfacing with telemetry and local workspace files via stdio JSON-RPC.

---

## 6. MCP Architecture

The Model Context Protocol (MCP) serves as the universal integration layer:
- **Client Implementation:** Python-based asynchronous JSON-RPC client running within the backend.
- **Telemetry Server (Custom Rust)** uses STDIO to expose log and deployment queries, runbooks, the release checklist, and local incident ticket creation.
- **Filesystem Server (Official MCP):** Restricted to release files under `mock_data/workspace/`. The telemetry server supplies runbooks and the release checklist as MCP resources.

---

## 7. Agent Workflow

1. Ingestion of alert payload and incident metadata.
2. Dynamic discovery of MCP tools via `tools/list`.
3. Iterative reasoning and telemetry querying (ReAct pattern).
4. Runbook retrieval and configuration analysis.
5. Hypothesis generation for root cause and release risk.
6. Execution of read-only diagnostic tools or safety-gated pausing for mutating actions.
7. Final synthesis of triage report and release recommendations.

---

## 8. Tool Discovery

The agent utilizes dynamic tool discovery at runtime:
- The backend queries connected MCP servers for JSON Schema definitions of available tools.
- Tool schemas are transformed into structured function-calling formats compatible with the underlying LLM.
- Tools are categorized dynamically into `READ_ONLY` diagnostics and `MUTATION` actions to enforce safety policies.

---

## 9. Safety and Human Approval

- **Risk Classification:** Tools are categorized based on their impact on system state.
- **Approval Interception:** Any tool call classified as a mutation suspends the execution loop and generates an approval request in the database.
- **Operator Review:** Operators inspect the action parameters, intended target, and risk profile in the UI, then either approve or reject the request.
- **Execution Safeguard:** No mutating tool can execute without a cryptographically verified or authenticated approval token.

---

## 10. Implementation

*(To be documented in subsequent phases as implementation proceeds.)*

### 10.1 Phase 0: Initialization and Scaffolding (Completed)
- Repository setup, branch verification (`develop`).
- Directory structure scaffolding for frontend, backend, MCP servers, mock data, and tests.
- Environment configuration (`.env`, `.env.example`, `.gitignore`).
- Architecture specification (`docs/ARCHITECTURE.md`).

### 10.2 Phase 1 — Repository Setup and Mock Data

| Work completed | Effect on the application |
| --- | --- |
| Added the assignment's `agent-client/` directory alongside the existing Rust server and web scaffolding. | Gives the MCP client and orchestrator a clear location. The web backend can call that component once it is implemented. |
| Seeded 44 logs across `auth-service`, `payments-api`, and `notification-worker`, with all four required severities. | Supports investigating a payments outage, a recovered authentication failure, and transient notification warnings. |
| Added deployment records with timestamps, commit hashes, versions, and rollback statuses. | Gives the agent a timeline to compare against the first checkout failures, with a known-good payments deployment for reference. |
| Added three service runbooks with symptoms, troubleshooting, escalation, and recovery sections, plus a shared release checklist. | Gives the telemetry server content for its two read-only resources and provides criteria for incident investigation and release readiness. |
| Added staging release notes, YAML configuration, and a JSON service manifest to `mock_data/workspace/`. | Lets a readiness check cross-check candidate versions and deployment IDs, compare the payments timeout of 250 ms with the 500 ms minimum, and corroborate the failed smoke test against telemetry. |
| Embedded a synthetic instruction in one payments error log. | Provides a fixture for verifying that the orchestrator treats tool results as data and bases its release verdict on evidence. |

The demo snapshot is `2026-11-20T04:30:00Z`. Payments deployment `pay-204` completed at 04:04 UTC. The first timeout occurred at 04:06 UTC, and the checkout smoke test subsequently failed. The timeline and configuration give an investigation enough evidence to identify the timeout change as the likely cause and flag the release as blocked.

Fixture validation passed for log counts, service coverage, severity values, unique IDs, deployment hashes, incident and recovery timing, runbook coverage, and agreement between the release notes, configuration, manifest, and deployment records. The unknown-service scenario uses `inventory-api`, which is absent from the fixtures.

### 10.3 Phase 2 — Custom Rust MCP Server

| Work completed | Effect on the application |
| --- | --- |
| Created the `ops-telemetry-mcp` Cargo project with a lockfile and a Tokio STDIO entry point. The MCP SDK handles JSON-RPC initialization, capability discovery, dispatch, and shutdown. | The orchestrator can launch the server as a child process and discover its capabilities at startup. |
| Registered `search_logs` and `get_deployment_history` with typed, required parameters. The server loads and validates the Phase 1 fixtures on startup. | The agent can filter messages by service and severity and correlate the results with deployments in a reproducible UTC time window. |
| Registered the release checklist and three concrete Markdown runbooks, plus a runbook URI template. | The agent can discover official release criteria and retrieve service-specific troubleshooting and escalation guidance through MCP. |
| Implemented `create_incident_ticket` with transactional SQLite writes and generated IDs. The tool returns the complete saved record with its UTC creation time. | The app can display the ticket after it is saved and retrieve it from `database/incidents.db` across restarts. Tool metadata marks this call as a write. The orchestrator will enforce approval before calling it. |
| Added structured failures for bad arguments, unknown services and resources, and failed writes. Startup diagnostics go to stderr. | The app can report actionable errors while the server remains available after an invalid request. MCP stdout stays reserved for protocol traffic. |

The Rust project uses the official MCP SDK for transport and registration, Tokio for async execution, Serde and `serde_json` for typed JSON, Chrono for UTC timestamps and time windows, `rusqlite` for the bundled SQLite store, and `thiserror` for startup and storage diagnostics. The SDK generates discoverable input schemas from the Rust models. `tempfile` provides isolated test databases. [Rust MCP SDK](https://github.com/modelcontextprotocol/rust-sdk) · [rusqlite](https://github.com/rusqlite/rusqlite)

On Windows, all five unit tests and all eight STDIO integration tests passed. The unit tests cover input validation, SQL persistence, and rollback when ID generation fails. The STDIO tests launch the compiled server with an SDK client and cover discovery, log filtering, deployment windows, Markdown reads, invalid requests, SQLite persistence across restarts and concurrent calls, and storage failures. The SQLite integration test reads the saved row directly and compares it with the MCP response.

A separate STDIO smoke test ran the sample requests for all three tools against the standalone build, verified the returned ticket against a temporary SQLite database, read the release checklist, and confirmed clean shutdown. Formatting, the build, and Clippy with warnings treated as errors also passed.

The Windows GNU build needed MinGW-w64 binutils and a C compiler to build the bundled SQLite library. The build was verified with those tools scoped to the local build session. The invalid-input test initially expected a JSON-RPC error. The SDK returns `isError: true` and a descriptive message for malformed tool arguments, so the test now checks that response and confirms the session stays usable.

The seeded instruction is returned as literal log text. How the agent responds to that text and whether it requests user approval before creating a ticket will be evaluated after orchestration is implemented.

### 10.4 Phase 3 — Filesystem MCP Integration

| Work completed | Effect on the application |
| --- | --- |
| Pinned the official Node.js filesystem server and added a Python MCP client that launches it over STDIO. | The application can connect to an existing MCP server, discover its tool schemas, and close the subprocess when its session ends. |
| Configured read-only mode with `mock_data/workspace/` as the sole allowed directory and confined legacy MCP Roots. The client verifies the active scope and validates paths before forwarding requests. | The agent can inspect staging release files within the permitted workspace. Read access outside it is denied by both layers and mutation tools are unavailable. |
| Exercised the three prepared workspace files through the app client. | A release readiness investigation can read the notes, YAML configuration, and service manifest to compare with telemetry. |

Seven tests passed on Windows. They verified tool discovery, directory listing, exact reads of all three fixtures, workspace configuration, and outside-path rejection. Direct SDK connections confirmed that the official server independently denies outside reads and listings, advertises only read-only tools, and confines a legacy client's broader Roots to the configured workspace.

A smoke test held both STDIO sessions open from Python, retrieved the latest payments error from the Rust server, and read the release notes from the official filesystem server. This demonstrates that one Python process can retrieve both sources of evidence.

### 10.5 Phase 3 — Python Agent Orchestrator

| Work completed | Effect on the application |
| --- | --- |
| Added a Python terminal agent that opens both MCP servers and a configurable model API client. | An operator can submit a triage or release readiness question from a single entry point. |
| Discovered both servers' read-only tool definitions, applied server prefixes, and exposed discovered telemetry resource URIs as an on-demand read function. | The model can choose the correct server and use its actual input schema. It can read a runbook or release checklist only when needed. |
| Built a loop that submits structured model tool calls over MCP and returns tool results under their original call IDs. | A result from one step can guide the next, so the agent can correlate logs, deployments, runbooks, and release files before summarizing. |
| Added a tool-call budget, per-call timeouts, error results, and JSONL traces. | Investigations stop after a configured number of calls, handle tool failures, and retain an audit of what was requested. |

The investigation passes tool results to the model as untrusted evidence and dispatches only registered read-only tools. Operator-approved writes and model behavior under adversarial inputs remain part of the safety phase.

All 10 Python tests passed on Windows. The investigation test uses scripted Chat Completions responses with both real MCP servers. It verifies six successive calls for logs, deployment history, the payments runbook, the release checklist, release notes, and the YAML configuration. Each result is sent back under its original tool-call ID. Additional tests cover malformed arguments, an unavailable write tool, a timeout, the call budget, and trace contents. A live model run requires the model name and API key, which were unset in the test environment.

### 10.6 Phase 4 — Safety & Approvals (Pending)
### 10.7 Phase 5 — Frontend Dashboard (Pending)

---

## 11. Evaluation and Benchmarking

*(Planned evaluation protocol to be executed in Phase 6.)*

Evaluation dimensions:
1. **Diagnostic Accuracy:** Precision and recall in identifying synthetic root causes across incident scenarios.
2. **Iteration Efficiency:** Distribution of iterations required to conclude triage (ceiling of 8).
3. **Safety Compliance Rate:** Guaranteeing 100% interception of mutating actions by the HITL gate.
4. **Latency Benchmarks:** Overhead introduced by MCP communication and LLM reasoning steps.

---

## 12. Results

*(Results, benchmark data, and metrics will be recorded here following experimental evaluation in Phase 6.)*

---

## 13. Limitations

*(To be identified and analyzed during testing and validation phases.)*
- Synthetic telemetry constraints versus live production distributed tracing systems.
- Context window trade-offs when processing voluminous log entries.
- Dependence on LLM tool-calling fidelity.

---

## 14. Future Improvements

*(To be refined in the final phases.)*
- Integration with live Prometheus, OpenTelemetry, and Datadog clusters.
- Multi-agent collaboration with specialized sub-agents (e.g., Log Specialist, Release Auditor).
- Automated regression runbook generation based on verified incident resolutions.

---

## 15. Conclusion

*(To be finalized upon project completion and benchmark analysis.)*
