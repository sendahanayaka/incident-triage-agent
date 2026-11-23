import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Server,
  AlertOctagon,
  GitBranch,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import { fetchServices } from '../api/services';
import { fetchIncidents } from '../api/incidents';
import { fetchDeployments } from '../api/deployments';
import { fetchPendingApprovals } from '../api/approvals';
import { ServiceResponse, IncidentResponse, DeploymentResponse, ApprovalResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { refreshCount } = useLayout();

  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [deployments, setDeployments] = useState<DeploymentResponse[]>([]);
  const [approvals, setApprovals] = useState<ApprovalResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [servicesData, incidentsData, deploymentsData, approvalsData] = await Promise.all([
        fetchServices(),
        fetchIncidents().catch(() => []),
        fetchDeployments().catch(() => []),
        fetchPendingApprovals().catch(() => []),
      ]);
      setServices(servicesData);
      setIncidents(incidentsData);
      setDeployments(deploymentsData);
      setApprovals(approvalsData);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData, refreshCount]);

  const totalDeploymentsCount = deployments.length || services.reduce((acc, s) => acc + (s.total_deployments || 0), 0);

  if (loading) {
    return <LoadingSpinner message="Loading telemetry and service overview..." />;
  }

  return (
    <div className="dashboard-page" data-testid="dashboard-page">
      {error && <ErrorBanner message={error} onRetry={loadDashboardData} />}

      {/* Operational Metrics Cards */}
      <div className="metrics-grid">
        <div className="metric-card" data-testid="metric-services">
          <div className="metric-info">
            <h3>Monitored Services</h3>
            <div className="metric-value">{services.length}</div>
          </div>
          <div className="metric-icon">
            <Server size={22} />
          </div>
        </div>

        <div className="metric-card" data-testid="metric-incidents">
          <div className="metric-info">
            <h3>Logged Incidents</h3>
            <div className="metric-value">{incidents.length}</div>
          </div>
          <div className="metric-icon" style={{ color: incidents.length > 0 ? 'var(--color-critical)' : undefined }}>
            <AlertOctagon size={22} />
          </div>
        </div>

        <div className="metric-card" data-testid="metric-deployments">
          <div className="metric-info">
            <h3>Total Deployments</h3>
            <div className="metric-value">{totalDeploymentsCount}</div>
          </div>
          <div className="metric-icon">
            <GitBranch size={22} />
          </div>
        </div>

        <div className="metric-card" data-testid="metric-approvals">
          <div className="metric-info">
            <h3>Pending Approvals</h3>
            <div className="metric-value" style={{ color: approvals.length > 0 ? 'var(--color-orange)' : undefined }}>
              {approvals.length}
            </div>
          </div>
          <div className="metric-icon" style={{ color: approvals.length > 0 ? 'var(--color-orange)' : undefined }}>
            <ShieldCheck size={22} />
          </div>
        </div>
      </div>

      {/* Pending HITL Gate Callout Banner if any */}
      {approvals.length > 0 && (
        <div
          style={{
            backgroundColor: '#fff7ed',
            border: '1px solid #fdba74',
            borderRadius: 'var(--radius-md)',
            padding: '16px 20px',
            marginBottom: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
          data-testid="pending-approvals-banner"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <ShieldCheck size={22} color="var(--color-orange)" />
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, color: '#9a3412' }}>
                {approvals.length} Mutation Action{approvals.length > 1 ? 's' : ''} Awaiting Human-in-the-Loop Review
              </div>
              <div style={{ fontSize: 12, color: '#c2410c', marginTop: 2 }}>
                High-risk actions require explicit operator review.
              </div>
            </div>
          </div>
          <button
            onClick={() => navigate('/approvals')}
            className="btn btn-primary btn-sm"
          >
            Review Approvals
          </button>
        </div>
      )}

      {/* Services Health Section */}
      <div className="card" style={{ marginBottom: 24 }} data-testid="dashboard-services-section">
        <div className="card-header">
          <div className="card-title">
            <Server size={18} color="var(--color-navy)" />
            <span>Operational Services Status</span>
          </div>
          <button
            onClick={() => navigate('/services')}
            className="btn btn-secondary btn-sm"
          >
            <span>View All</span>
            <ArrowRight size={14} />
          </button>
        </div>

        {services.length === 0 ? (
          <EmptyState
            title="No Services Discovered"
            description="The operational backend did not return any active services."
          />
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Latest Deployment</th>
                  <th>Error Count</th>
                  <th>Runbook</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc) => (
                  <tr key={svc.service_name} data-testid={`service-row-${svc.service_name}`}>
                    <td style={{ fontWeight: 600 }}>{svc.service_name}</td>
                    <td>
                      <StatusBadge status={svc.status} variant="service" />
                    </td>
                    <td>
                      {svc.latest_deployment_version ? (
                        <span className="mono-text">{svc.latest_deployment_version}</span>
                      ) : (
                        <span style={{ color: 'var(--color-text-muted)' }}>None</span>
                      )}
                    </td>
                    <td>
                      <span
                        style={{
                          fontWeight: 600,
                          color: svc.error_count > 0 ? 'var(--color-critical)' : 'inherit',
                        }}
                      >
                        {svc.error_count}
                      </span>
                    </td>
                    <td>
                      {svc.runbook_available ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            fontSize: 12,
                            color: 'var(--color-success)',
                          }}
                        >
                          <BookOpen size={14} /> Available
                        </span>
                      ) : (
                        <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>No runbook</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/investigations?service=${encodeURIComponent(svc.service_name)}`)}
                        data-testid={`investigate-btn-${svc.service_name}`}
                      >
                        <Sparkles size={12} color="var(--color-orange)" />
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Grid: Recent Incidents & Recent Deployments */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 24 }}>
        {/* Recent Incidents Card */}
        <div className="card" data-testid="dashboard-incidents-section">
          <div className="card-header">
            <div className="card-title">
              <AlertOctagon size={18} color="var(--color-critical)" />
              <span>Recent Incident Tickets</span>
            </div>
            <button
              onClick={() => navigate('/incidents')}
              className="btn btn-secondary btn-sm"
            >
              <span>View All</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {incidents.length === 0 ? (
            <EmptyState
              title="No Incidents Reported"
              description="No active or historical incident tickets exist in the SQLite database."
            />
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ticket ID</th>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>Assignee</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.slice(0, 5).map((inc) => (
                    <tr key={inc.ticket_id}>
                      <td className="mono-text" style={{ fontWeight: 600 }}>{inc.ticket_id}</td>
                      <td>
                        <StatusBadge status={inc.severity} variant="severity" />
                      </td>
                      <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {inc.title}
                      </td>
                      <td>{inc.assignee}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Deployments Card */}
        <div className="card" data-testid="dashboard-deployments-section">
          <div className="card-header">
            <div className="card-title">
              <GitBranch size={18} color="var(--color-navy)" />
              <span>Recent Deployments</span>
            </div>
            <button
              onClick={() => navigate('/deployments')}
              className="btn btn-secondary btn-sm"
            >
              <span>View All</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {deployments.length === 0 ? (
            <EmptyState
              title="No Deployments Found"
              description="No recent deployment history is available from the telemetry service."
            />
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Deployment</th>
                    <th>Service</th>
                    <th>Version</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {deployments.slice(0, 5).map((dep) => (
                    <tr key={dep.deployment_id}>
                      <td className="mono-text">{dep.deployment_id}</td>
                      <td style={{ fontWeight: 600 }}>{dep.service_name}</td>
                      <td>
                        <span className="mono-text">{dep.version}</span>
                      </td>
                      <td>
                        <StatusBadge status={dep.status} variant="deployment" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
