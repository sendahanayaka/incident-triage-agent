# Manual Testing Guide: Incident Triage & Release Readiness Agent

This guide provides end-to-end instructions for manually exploring, demonstrating, and testing the entire application in **Offline Mode** (or Live Mode with OpenRouter).

---

## 1. System Architecture & Startup

The application consists of three primary components:
1. **Rust Telemetry MCP Server:** Provides tools for querying mock logs, deployment history, and runbook resources.
2. **FastAPI Backend (Port 8000):** Orchestrates investigations, SQLite persistence, and REST APIs.
3. **React + Vite Frontend (Port 5173):** Interactive operational dashboard.

### Starting the Backend
In your project terminal:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify backend readiness by navigating to `http://localhost:8000/api/health` in your browser. You should see:
```json
{
  "status": "healthy",
  "application": "Incident Triage & Release Readiness Agent",
  "version": "1.0.0",
  "environment": "development",
  "llm": {
    "provider": "offline",
    "mode": "offline",
    "model": "offline/incident-triage-v1",
    "base_url": "https://openrouter.ai/api/v1",
    "has_api_key": false,
    "is_ready": true
  }
}
```

### Starting the Frontend
In a second terminal:
```powershell
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 2. Walkthrough of Application Pages

### Page 1: Dashboard (`/`)
- **Header:** Displays connectivity status (`FastAPI Connected`) and runtime LLM status pill (`LLM: OFFLINE (offline)`).
- **Runtime Status Banner:** Outlines current active provider, execution mode, model ID, and API key status.
- **Metrics Grid:** Shows 4 real-time operational cards:
  - Monitored Services (3)
  - Logged Incidents
  - Total Deployments (4)
  - Pending Approvals (HITL gate)
- **Services Table:** Quick overview of `auth-service`, `payments-api`, and `notification-worker`. Click **Investigate** on any service to navigate straight to the triage console with a pre-filled query.

### Page 2: Service Directory (`/services`)
- Displays detailed cards for each monitored microservice.
- View service health tags (`HEALTHY`, `DEGRADED`), recent deployment versions, total historical error count, and runbook availability.
- Click **View Runbook** to view the operational markdown runbook.
- Click **Start Investigation** to launch a root cause analysis for that service.

### Page 3: Incident Investigations (`/investigations`)
- This is the interactive AI triage console.
- **Quick Scenarios:** Click one of the quick scenario pills:
  - *Scenario A: Payments API 504 Errors (Deployment pay-204 timeout)*
  - *Scenario B: Auth Service Token Validation Anomaly (Cache miss)*
  - *Scenario C: Release Checklist Verification (Promotion readiness)*
  - *Scenario D: Payment Gateway Outage Ticket Proposal (HITL gate)*
- **Execute Investigation:** Click **Run Investigation**. In offline mode, the agent performs multi-step ReAct reasoning in memory with zero external API calls.
- **View Results:**
  - Synthesized Markdown root cause findings.
  - Evidence citations badge list (`LOG-019`, `LOG-020`, `pay-204`, etc.).
  - Actionable recommendations.
  - Interactive table of tools invoked by the agent (`telemetry__search_logs`, `telemetry__get_deployment_history`, etc.).

### Page 4: Incident Tickets (`/incidents`)
- Lists all operational incident tickets persisted in the SQLite database (`incidents.db`).
- Filter tickets by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) or search by keyword.
- Inspect ticket title, creation timestamp, summary, and assignee.

### Page 5: Human-in-the-Loop Approvals (`/approvals`)
- Implements safety guardrails: state-mutating actions (such as `create_incident_ticket`) are held in a pending state until authorized by a human operator.
- Click **Approve** to authorize the proposal. A confirmation modal will appear requiring explicit confirmation. Upon approval, the ticket is persisted in the database.
- Click **Reject** to deny the proposal. The agent records the human rejection in the trace log and aborts the mutation tool.

### Page 6: Telemetry Logs (`/logs`)
- Explore raw operational telemetry logs.
- Filter by microservice (`payments-api`, `auth-service`, `notification-worker`) and severity (`INFO`, `WARN`, `ERROR`, `FATAL`).
- Inspect timestamps, log IDs, and event descriptions.

### Page 7: Deployment History (`/deployments`)
- Review historical deployments across services.
- Inspect deployment IDs (`pay-204`, `pay-203`, `auth-087`), commit hashes, versions, and rollback readiness indicators.

### Page 8: Agent Execution Traces (`/traces`)
- View execution traces captured in JSONL format.
- Inspect tool execution run IDs, tool names, execution duration in milliseconds, argument payloads, and HITL authorization decisions.

---

## 3. How to Test the Human-in-the-Loop (HITL) Gate

1. Navigate to **Investigations** (`/investigations`).
2. Click the quick button **"Scenario D: Payment Gateway Outage Ticket Proposal"** (or type a query containing `propose incident ticket for payments outage`).
3. Click **Run Investigation**.
4. The agent will analyze telemetry, detect the severity, and propose creating an incident ticket via the `telemetry__create_incident_ticket` mutation tool.
5. Navigate to **HITL Approvals** (`/approvals`) or look at the orange callout banner on the **Dashboard**.
6. You will see the pending ticket authorization request.
7. **To Test Approval:**
   - Click the green **Approve** button.
   - Confirm in the modal dialog.
   - The approval count decrements to 0, and the new ticket appears under **Incident Tickets** (`/incidents`).
8. **To Test Rejection:**
   - Trigger another ticket proposal.
   - Click the red **Reject** button.
   - Confirm in the modal dialog.
   - The action is marked as rejected, the ticket is NOT persisted, and the rejection is audited in **Agent Traces** (`/traces`).
