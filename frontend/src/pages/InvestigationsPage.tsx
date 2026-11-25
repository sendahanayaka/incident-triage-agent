import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Sparkles,
  Terminal,
  CheckCircle,
  XCircle,
  FileText,
  Lightbulb,
  ShieldAlert,
} from 'lucide-react';
import { startInvestigation } from '../api/investigations';
import { fetchPendingApprovals, approvePendingAction, rejectPendingAction } from '../api/approvals';
import { InvestigationResponse, ApprovalResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { getErrorMessage } from '../api/client';
import { useLayout } from '../components/layout/AppLayout';

export const InvestigationsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const serviceParam = searchParams.get('service');
  const { triggerRefresh } = useLayout();

  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigationResponse | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalResponse[]>([]);
  const [decisionFeedback, setDecisionFeedback] = useState<{ id: string; status: 'approved' | 'rejected'; message: string } | null>(null);
  const [decisionLoading, setDecisionLoading] = useState<boolean>(false);

  useEffect(() => {
    if (serviceParam) {
      setQuery(`Investigate ${serviceParam} and determine root cause of recent errors or release readiness.`);
    }
  }, [serviceParam]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || query.trim().length < 3) return;

    setLoading(true);
    setError(null);
    setDecisionFeedback(null);
    try {
      const response = await startInvestigation({ query: query.trim() });
      setResult(response);
      try {
        const hasPendingMutation =
          Boolean(response.pending_approval) ||
          response.tool_calls.some(
            (t) => t.tool.includes('create_incident_ticket') && (t.status === 'pending_approval' || t.status === 'pending')
          );

        if (hasPendingMutation) {
          if (response.pending_approval) {
            setPendingApprovals([response.pending_approval]);
          } else {
            const pending = await fetchPendingApprovals();
            const ticketCall = response.tool_calls.find((t) => t.tool.includes('create_incident_ticket'));
            const expectedTitle =
              ticketCall && typeof ticketCall.arguments === 'object' && ticketCall.arguments !== null && 'title' in ticketCall.arguments
                ? String(ticketCall.arguments.title).toLowerCase()
                : '';
            const matched = pending.find((p) => {
              const pTitle = String(p.parameters?.title || '').toLowerCase();
              return expectedTitle && pTitle && (pTitle.includes(expectedTitle) || expectedTitle.includes(pTitle));
            });
            setPendingApprovals(matched ? [matched] : (pending.length > 0 ? [pending[0]] : []));
          }
        } else {
          // Strictly read-only investigation: no approval card
          setPendingApprovals([]);
        }
        triggerRefresh();
      } catch {
        setPendingApprovals([]);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAction = async (approvalId: string) => {
    setDecisionLoading(true);
    try {
      const decision = await approvePendingAction(approvalId, { operator: 'operator', note: 'Approved from Investigation Console' });
      const execRes = decision.execution_result;
      const ticketId = execRes && typeof execRes === 'object' && 'ticket_id' in execRes
        ? String(execRes.ticket_id)
        : '';
      setDecisionFeedback({
        id: approvalId,
        status: 'approved',
        message: ticketId
          ? `Action approved! Incident ticket ${ticketId} was successfully created and recorded in SQLite database.`
          : 'Action approved and executed successfully.',
      });
      setPendingApprovals((prev) => prev.filter((a) => a.id !== approvalId));
      triggerRefresh();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDecisionLoading(false);
    }
  };

  const handleRejectAction = async (approvalId: string) => {
    setDecisionLoading(true);
    try {
      await rejectPendingAction(approvalId, { operator: 'operator', note: 'Rejected from Investigation Console' });
      setDecisionFeedback({
        id: approvalId,
        status: 'rejected',
        message: 'Action rejected by operator. Mutation tool was aborted.',
      });
      setPendingApprovals((prev) => prev.filter((a) => a.id !== approvalId));
      triggerRefresh();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDecisionLoading(false);
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    setQuery(prompt);
  };

  return (
    <div className="investigations-page" data-testid="investigations-page">
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 14, color: 'var(--color-text-secondary)' }}>
          Submit natural language queries to the bounded ReAct agent orchestrator. The agent searches telemetry logs, deployment records, runbooks, and release checklists before synthesizing evidence-based recommendations.
        </p>
      </div>

      {error && <ErrorBanner title="Investigation Execution Failed" message={error} />}

      {/* Query Submission Card */}
      <div className="card" style={{ marginBottom: 24 }}>
        <form onSubmit={handleSubmit} data-testid="investigation-form">
          <div className="form-group">
            <label className="form-label" htmlFor="investigation-query">
              Investigation Query or Triage Goal:
            </label>
            <textarea
              id="investigation-query"
              className="form-textarea"
              rows={3}
              placeholder="e.g. Investigate payments-api and identify the cause of recent 500 error spikes, or check if auth-service is ready for release."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
              required
              minLength={3}
              maxLength={2000}
              data-testid="investigation-input"
            />
          </div>

          {/* Quick Scenario Templates */}
          <div style={{ marginBottom: 16 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginRight: 8 }}>
              Sample Scenarios:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleQuickPrompt('Investigate payments-api: search logs for recent 500 errors and check deployment pay-204.')}
                disabled={loading}
              >
                Payments API Triage
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleQuickPrompt('Assess release readiness for auth-service v2.1.0 using the release checklist and test logs.')}
                disabled={loading}
              >
                Auth Service Release Readiness
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleQuickPrompt('Check notification-worker for retry exhaustion and queue lag symptoms.')}
                disabled={loading}
              >
                Notification Worker Audit
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              Bounded to 8 ReAct iterations with Human-in-the-Loop safeguards on mutations.
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !query.trim() || query.trim().length < 3}
              data-testid="start-investigation-btn"
            >
              {loading ? (
                <>
                  <div className="spinner" style={{ width: 14, height: 14, borderTopColor: '#ffffff' }} />
                  <span>Agent Triage in Progress...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Start AI Investigation</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Loading State Animation */}
      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '40px 24px', marginBottom: 24 }} data-testid="investigation-loading">
          <div className="spinner" style={{ width: 36, height: 36, margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-navy)', marginBottom: 8 }}>
            Running Agentic ReAct Investigation
          </h3>
          <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', maxWidth: 500, margin: '0 auto' }}>
            The agent is executing bounded tool calls across the Rust operational telemetry MCP server and sandboxed filesystem MCP to gather evidence...
          </p>
        </div>
      )}

      {/* Investigation Results Display */}
      {result && !loading && (
        <div className="investigation-result" data-testid="investigation-result">
          {/* Header Metadata Banner */}
          <div
            style={{
              backgroundColor: 'var(--color-card)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '18px 24px',
              marginBottom: 20,
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Investigation Result</h3>
                  <StatusBadge status={result.status} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                  Run ID: <span className="mono-text" style={{ fontWeight: 600 }}>{result.id}</span> | Completed: {result.completed_at ? new Date(result.completed_at).toLocaleTimeString() : 'N/A'}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                <div>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Tools Invoked: </span>
                  <span style={{ fontWeight: 700 }}>{result.tool_calls.length}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Evidence Citations: </span>
                  <span style={{ fontWeight: 700 }}>{result.evidence.length}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Feedback Banner after Decision */}
          {decisionFeedback && (
            <div
              style={{
                marginBottom: 20,
                padding: '14px 18px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: decisionFeedback.status === 'approved' ? '#f0fdf4' : '#fef2f2',
                border: `1px solid ${decisionFeedback.status === 'approved' ? '#86efac' : '#fca5a5'}`,
                color: decisionFeedback.status === 'approved' ? '#166534' : '#991b1b',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                fontSize: 14,
                fontWeight: 500,
              }}
              data-testid="decision-feedback-banner"
            >
              {decisionFeedback.status === 'approved' ? <CheckCircle size={18} /> : <XCircle size={18} />}
              <span>{decisionFeedback.message}</span>
            </div>
          )}

          {/* HITL Pending Approval Gate Card */}
          {pendingApprovals.map((app) => (
            <div
              key={app.id}
              className="card"
              style={{
                marginBottom: 20,
                backgroundColor: '#fffbeb',
                border: '2px solid #f59e0b',
                borderRadius: 'var(--radius-md)',
                padding: '20px 24px',
                boxShadow: '0 4px 6px -1px rgba(245, 158, 11, 0.15)',
              }}
              data-testid="hitl-pending-approval-card"
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
                <div style={{ display: 'flex', gap: 14, width: '100%' }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      backgroundColor: '#fef3c7',
                      color: '#d97706',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <ShieldAlert size={22} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#92400e' }}>
                        Action Requires Human-in-the-Loop Confirmation
                      </h4>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: 12,
                          backgroundColor: '#fee2e2',
                          color: '#b91c1c',
                        }}
                      >
                        MUTATION ACTION
                      </span>
                    </div>
                    <p style={{ margin: '6px 0 12px', fontSize: 13, color: '#78350f' }}>
                      {app.description}
                    </p>

                    {/* Parameters Preview */}
                    <div
                      style={{
                        backgroundColor: '#ffffff',
                        border: '1px solid #fde68a',
                        borderRadius: 'var(--radius-sm)',
                        padding: '12px 16px',
                        fontSize: 13,
                        marginBottom: 14,
                      }}
                    >
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
                        {Object.entries(app.parameters).map(([key, val]) => (
                          <div key={key}>
                            <span style={{ fontWeight: 600, color: 'var(--color-navy)', textTransform: 'capitalize' }}>
                              {key}:{' '}
                            </span>
                            <span style={{ color: 'var(--color-text)' }}>{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        style={{ backgroundColor: '#16a34a', borderColor: '#15803d' }}
                        onClick={() => handleApproveAction(app.id)}
                        disabled={decisionLoading}
                        data-testid="approve-ticket-btn"
                      >
                        <CheckCircle size={15} />
                        <span>Approve &amp; Create Ticket</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                        onClick={() => handleRejectAction(app.id)}
                        disabled={decisionLoading}
                        data-testid="reject-ticket-btn"
                      >
                        <XCircle size={15} />
                        <span>Reject Action</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Synthesized Findings */}
          <div className="card" style={{ marginBottom: 20 }} data-testid="findings-section">
            <div className="card-header">
              <div className="card-title">
                <FileText size={18} color="var(--color-navy)" />
                <span>Synthesized Findings & Root Cause</span>
              </div>
            </div>
            <div
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: 'var(--color-text)',
                whiteSpace: 'pre-wrap',
                backgroundColor: '#fafbfc',
                padding: '16px 20px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              {result.findings}
            </div>
          </div>

          {/* Evidence Citations & Remediation Recommendations Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 20, marginBottom: 20 }}>
            {/* Evidence List */}
            <div className="card" data-testid="evidence-section">
              <div className="card-header">
                <div className="card-title">
                  <CheckCircle size={18} color="var(--color-success)" />
                  <span>Evidence Citations ({result.evidence.length})</span>
                </div>
              </div>
              {result.evidence.length === 0 ? (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
                  No explicit citations extracted.
                </div>
              ) : (
                <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {result.evidence.map((item, idx) => (
                    <li
                      key={idx}
                      style={{
                        fontSize: 13,
                        padding: '10px 14px',
                        backgroundColor: '#f8fafc',
                        borderLeft: '3px solid var(--color-success)',
                        borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                      }}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Recommendations List */}
            <div className="card" data-testid="recommendations-section">
              <div className="card-header">
                <div className="card-title">
                  <Lightbulb size={18} color="var(--color-orange)" />
                  <span>Remediation Recommendations ({result.recommendations.length})</span>
                </div>
              </div>
              {result.recommendations.length === 0 ? (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
                  No actionable recommendations provided.
                </div>
              ) : (
                <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {result.recommendations.map((item, idx) => (
                    <li
                      key={idx}
                      style={{
                        fontSize: 13,
                        padding: '10px 14px',
                        backgroundColor: '#fffbeb',
                        borderLeft: '3px solid var(--color-orange)',
                        borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                      }}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Tool Invocations Timeline */}
          <div className="card" data-testid="tool-calls-section">
            <div className="card-header">
              <div className="card-title">
                <Terminal size={18} color="var(--color-navy)" />
                <span>Agent Tool Execution Timeline ({result.tool_calls.length} calls)</span>
              </div>
            </div>

            {result.tool_calls.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
                Zero tool calls invoked during this investigation.
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Tool Name</th>
                      <th>Duration</th>
                      <th>Status</th>
                      <th>Parameters</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.tool_calls.map((call, idx) => (
                      <tr key={idx}>
                        <td style={{ color: 'var(--color-text-muted)' }}>{idx + 1}</td>
                        <td className="mono-text" style={{ fontWeight: 600, color: 'var(--color-navy)' }}>
                          {call.tool}
                        </td>
                        <td>
                          {call.duration_ms != null ? (
                            <span style={{ fontSize: 12 }}>{call.duration_ms.toFixed(1)} ms</span>
                          ) : (
                            <span style={{ color: 'var(--color-text-muted)' }}>-</span>
                          )}
                        </td>
                        <td>
                          <StatusBadge status={call.status} />
                        </td>
                        <td>
                          <details style={{ fontSize: 12, cursor: 'pointer' }}>
                            <summary style={{ color: 'var(--color-navy)', outline: 'none' }}>
                              View arguments
                            </summary>
                            <pre
                              style={{
                                marginTop: 6,
                                padding: 8,
                                backgroundColor: '#1e293b',
                                color: '#f8fafc',
                                borderRadius: 4,
                                overflowX: 'auto',
                                fontSize: 11,
                              }}
                            >
                              {JSON.stringify(call.arguments, null, 2)}
                            </pre>
                          </details>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
