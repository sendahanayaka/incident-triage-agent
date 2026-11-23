import React, { useEffect, useState, useCallback } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle, XCircle, AlertTriangle, User, Clock } from 'lucide-react';
import { fetchPendingApprovals, approvePendingAction, rejectPendingAction } from '../api/approvals';
import { ApprovalResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const ApprovalsPage: React.FC = () => {
  const { refreshCount, triggerRefresh } = useLayout();

  const [approvals, setApprovals] = useState<ApprovalResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modal State
  const [activeApproval, setActiveApproval] = useState<ApprovalResponse | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'reject' | null>(null);
  const [operator, setOperator] = useState<string>('operator');
  const [note, setNote] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);

  const loadApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPendingApprovals();
      setApprovals(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals, refreshCount]);

  const handleOpenConfirm = (approval: ApprovalResponse, type: 'approve' | 'reject') => {
    setActiveApproval(approval);
    setActionType(type);
    setOperator('operator');
    setNote('');
  };

  const handleCloseModal = () => {
    setActiveApproval(null);
    setActionType(null);
    setSubmitting(false);
  };

  const handleConfirmDecision = async () => {
    if (!activeApproval || !actionType) return;

    setSubmitting(true);
    setError(null);
    try {
      if (actionType === 'approve') {
        const result = await approvePendingAction(activeApproval.id, {
          operator: operator.trim() || 'operator',
          note: note.trim() || undefined,
        });
        setSuccessMessage(`Approval executed successfully: ${result.message}`);
      } else {
        const result = await rejectPendingAction(activeApproval.id, {
          operator: operator.trim() || 'operator',
          note: note.trim() || undefined,
        });
        setSuccessMessage(`Action rejected: ${result.message}`);
      }
      handleCloseModal();
      loadApprovals();
      triggerRefresh();
    } catch (err) {
      setError(getErrorMessage(err));
      setSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Checking for pending Human-in-the-Loop approvals..." />;
  }

  return (
    <div className="approvals-page" data-testid="approvals-page">
      {error && <ErrorBanner message={error} onRetry={loadApprovals} />}
      {successMessage && (
        <div
          style={{
            backgroundColor: 'var(--color-success-bg)',
            border: '1px solid var(--color-success-border)',
            color: 'var(--color-success)',
            padding: '14px 20px',
            borderRadius: 'var(--radius-md)',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <CheckCircle size={18} />
            <span style={{ fontSize: 13.5, fontWeight: 600 }}>{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="btn btn-secondary btn-sm"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* HITL Architecture Explanation Callout */}
      <div
        style={{
          backgroundColor: '#eff6ff',
          borderLeft: '4px solid var(--color-navy)',
          padding: '14px 20px',
          marginBottom: 24,
          borderRadius: '0 var(--radius-md) var(--radius-md) 0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <ShieldAlert size={20} color="var(--color-navy)" style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-navy)', margin: 0 }}>
              Human-in-the-Loop (HITL) Safety Policy
            </h4>
            <p style={{ fontSize: 13, color: '#1e3a8a', marginTop: 4, lineHeight: 1.5, margin: 0 }}>
              Autonomous mutation tools (such as <code>create_incident_ticket</code>) are strictly prohibited from executing automatically. In CLI workflows, the agent halts and prompts an operator via stdin. In the backend environment, proposed actions are staged in this approval queue and require explicit operator confirmation before execution.
            </p>
          </div>
        </div>
      </div>

      {approvals.length === 0 ? (
        <EmptyState
          title="No Pending Approvals"
          description="All proposed mutation actions have been reviewed or none are currently queued."
          icon={<ShieldCheck size={44} color="var(--color-success)" />}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {approvals.map((approval) => (
            <div key={approval.id} className="card" data-testid={`approval-card-${approval.id}`}>
              <div className="card-header" style={{ marginBottom: 14, paddingBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span className="mono-text" style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-navy)' }}>
                    {approval.id}
                  </span>
                  <StatusBadge status={approval.risk_level} variant="approval" />
                  <span className="mono-text" style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-orange)' }}>
                    {approval.action_type}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12, color: 'var(--color-text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <User size={13} /> Requested by: {approval.requested_by}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={13} /> {new Date(approval.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)', marginBottom: 4 }}>
                  Action Description:
                </div>
                <div style={{ fontSize: 13.5, color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                  {approval.description}
                </div>
              </div>

              {/* Parameters Preview */}
              <div style={{ marginBottom: 18 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6 }}>
                  Execution Parameters:
                </div>
                <pre
                  style={{
                    backgroundColor: '#1e293b',
                    color: '#f8fafc',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 12,
                    fontFamily: 'var(--font-mono)',
                    overflowX: 'auto',
                  }}
                >
                  {JSON.stringify(approval.parameters, null, 2)}
                </pre>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleOpenConfirm(approval, 'reject')}
                  data-testid={`reject-btn-${approval.id}`}
                >
                  <XCircle size={15} color="var(--color-critical)" />
                  <span>Reject Action</span>
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => handleOpenConfirm(approval, 'approve')}
                  data-testid={`approve-btn-${approval.id}`}
                >
                  <CheckCircle size={15} />
                  <span>Approve & Execute</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Confirmation Modal */}
      {activeApproval && actionType && (
        <div className="modal-overlay" data-testid="approval-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertTriangle size={18} color={actionType === 'approve' ? 'var(--color-orange)' : 'var(--color-critical)'} />
                <span>Confirm Action {actionType === 'approve' ? 'Approval' : 'Rejection'}</span>
              </h3>
            </div>

            <div className="modal-body">
              <p style={{ fontSize: 13.5, color: 'var(--color-text-secondary)', marginBottom: 16 }}>
                You are about to <strong>{actionType.toUpperCase()}</strong> the following action:
              </p>
              <div
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  marginBottom: 16,
                  fontSize: 13,
                }}
              >
                <div>ID: <span className="mono-text" style={{ fontWeight: 600 }}>{activeApproval.id}</span></div>
                <div>Action: <span className="mono-text" style={{ fontWeight: 600 }}>{activeApproval.action_type}</span></div>
                <div>Risk: <strong>{activeApproval.risk_level}</strong></div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="operator-name">
                  Operator Identifier:
                </label>
                <input
                  id="operator-name"
                  type="text"
                  className="form-input"
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                  placeholder="e.g. alice, sreadmin"
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="decision-note">
                  Audit Note / Rationale (optional):
                </label>
                <input
                  id="decision-note"
                  type="text"
                  className="form-input"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. Verified logs confirm payment gateway timeout"
                />
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={handleCloseModal}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                className={actionType === 'approve' ? 'btn btn-primary' : 'btn btn-danger'}
                onClick={handleConfirmDecision}
                disabled={submitting || !operator.trim()}
                data-testid="modal-confirm-btn"
              >
                {submitting ? 'Executing...' : actionType === 'approve' ? 'Confirm Approval' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
