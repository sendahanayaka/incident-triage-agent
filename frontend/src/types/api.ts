/**
 * API Data Models matching FastAPI Backend Contracts.
 * Never invent fields or types that do not exist in the backend models.
 */

export interface HealthResponse {
  status: string;
  application: string;
  version: string;
  environment: string;
}

export interface ServiceResponse {
  service_name: string;
  status: 'healthy' | 'degraded' | 'critical' | string;
  runbook_available: boolean;
  total_deployments: number;
  error_count: number;
  latest_deployment_version: string | null;
  latest_deployment_time: string | null;
  description: string | null;
}

export interface LogEntryResponse {
  id: string;
  timestamp: string;
  service_name: string;
  severity: 'INFO' | 'WARN' | 'ERROR' | 'FATAL' | string;
  event: string;
  message: string;
}

export interface DeploymentResponse {
  deployment_id: string;
  service_name: string;
  version: string;
  commit_hash: string;
  timestamp: string;
  status: string;
  rollback_status: string;
  summary: string;
}

export interface IncidentResponse {
  ticket_id: string;
  created_at: string;
  title: string;
  severity: string;
  summary: string;
  assignee: string;
}

export interface ToolCallRecord {
  tool: string;
  arguments: Record<string, unknown>;
  status: string;
  duration_ms: number | null;
}

export interface InvestigationResponse {
  id: string;
  query: string;
  status: 'completed' | 'failed' | 'in_progress' | string;
  findings: string;
  evidence: string[];
  recommendations: string[];
  tool_calls: ToolCallRecord[];
  created_at: string;
  completed_at: string | null;
}

export interface InvestigationDetail extends InvestigationResponse {
  error_message?: string | null;
}

export interface InvestigationRequest {
  query: string;
}

export interface ApprovalResponse {
  id: string;
  action_type: string;
  description: string;
  parameters: Record<string, unknown>;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string;
  status: 'pending' | 'approved' | 'rejected' | string;
  created_at: string;
  requested_by: string;
  decision_at: string | null;
  decision_by: string | null;
  execution_status: 'pending' | 'executed' | 'failed' | 'skipped' | string;
  execution_result: Record<string, unknown> | null;
}

export interface ApprovalDecisionRequest {
  operator?: string;
  note?: string | null;
}

export interface ApprovalDecisionResponse {
  approval_id: string;
  status: 'approved' | 'rejected' | string;
  action_type: string;
  execution_status: 'executed' | 'skipped' | 'failed' | string;
  execution_result: Record<string, unknown> | null;
  message: string;
}

export interface TraceResponse {
  timestamp: string;
  run_id: string;
  tool: string;
  arguments: Record<string, unknown>;
  duration_ms: number;
  status: 'ok' | 'error' | 'timeout' | string;
  mcp_server: string | null;
}
