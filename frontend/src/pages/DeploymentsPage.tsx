import React, { useEffect, useState, useCallback } from 'react';
import { GitBranch, Filter } from 'lucide-react';
import { fetchDeployments } from '../api/deployments';
import { fetchServices } from '../api/services';
import { DeploymentResponse, ServiceResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const DeploymentsPage: React.FC = () => {
  const { refreshCount } = useLayout();

  const [deployments, setDeployments] = useState<DeploymentResponse[]>([]);
  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [selectedService, setSelectedService] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchServices()
      .then((data) => setServices(data))
      .catch(() => setServices([]));
  }, []);

  const loadDeployments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDeployments({
        service: selectedService || undefined,
      });
      setDeployments(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [selectedService]);

  useEffect(() => {
    loadDeployments();
  }, [loadDeployments, refreshCount]);

  return (
    <div className="deployments-page" data-testid="deployments-page">
      {error && <ErrorBanner message={error} onRetry={loadDeployments} />}

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={16} color="var(--color-text-secondary)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Filter by Service:</span>
          </div>

          <div style={{ minWidth: 200 }}>
            <select
              className="form-select"
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              aria-label="Filter by Service"
              data-testid="filter-deployment-service"
            >
              <option value="">All Services</option>
              {services.map((svc) => (
                <option key={svc.service_name} value={svc.service_name}>
                  {svc.service_name}
                </option>
              ))}
            </select>
          </div>

          {selectedService && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedService('')}
            >
              Reset Filter
            </button>
          )}

          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-text-secondary)' }}>
            Showing <strong>{deployments.length}</strong> deployment records
          </div>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Retrieving deployment records from telemetry service..." />
      ) : deployments.length === 0 ? (
        <EmptyState
          title="No Deployments Found"
          description="No deployment records match the selected service filter."
          icon={<GitBranch size={44} />}
        />
      ) : (
        <div className="table-container">
          <table className="data-table" data-testid="deployments-table">
            <thead>
              <tr>
                <th style={{ width: 110 }}>Deployment</th>
                <th style={{ width: 150 }}>Service</th>
                <th style={{ width: 110 }}>Version</th>
                <th style={{ width: 120 }}>Commit</th>
                <th style={{ width: 180 }}>Timestamp</th>
                <th style={{ width: 110 }}>Status</th>
                <th style={{ width: 130 }}>Rollback</th>
                <th>Release Summary</th>
              </tr>
            </thead>
            <tbody>
              {deployments.map((dep) => (
                <tr key={dep.deployment_id} data-testid={`deployment-row-${dep.deployment_id}`}>
                  <td className="mono-text" style={{ fontWeight: 600, color: 'var(--color-navy)' }}>
                    {dep.deployment_id}
                  </td>
                  <td style={{ fontWeight: 600 }}>{dep.service_name}</td>
                  <td>
                    <span className="mono-text" style={{ fontWeight: 600 }}>{dep.version}</span>
                  </td>
                  <td>
                    <span
                      className="mono-text"
                      style={{
                        fontSize: 11.5,
                        backgroundColor: '#f1f5f9',
                        padding: '2px 6px',
                        borderRadius: 4,
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {dep.commit_hash.slice(0, 7)}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                    {new Date(dep.timestamp).toLocaleString()}
                  </td>
                  <td>
                    <StatusBadge status={dep.status} variant="deployment" />
                  </td>
                  <td>
                    <span
                      style={{
                        fontSize: 11.5,
                        fontWeight: 600,
                        color: dep.rollback_status === 'rolled_back' ? 'var(--color-critical)' : 'var(--color-text-secondary)',
                      }}
                    >
                      {dep.rollback_status}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--color-text)' }}>
                    {dep.summary}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
