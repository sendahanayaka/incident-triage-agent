import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Server, BookOpen, AlertCircle, Sparkles, GitBranch, Clock } from 'lucide-react';
import { fetchServices } from '../api/services';
import { ServiceResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const ServicesPage: React.FC = () => {
  const navigate = useNavigate();
  const { refreshCount } = useLayout();

  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadServices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchServices();
      setServices(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadServices();
  }, [loadServices, refreshCount]);

  if (loading) {
    return <LoadingSpinner message="Querying monitored operational services..." />;
  }

  return (
    <div className="services-page" data-testid="services-page">
      {error && <ErrorBanner message={error} onRetry={loadServices} />}

      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 14, color: 'var(--color-text-secondary)' }}>
          Operational microservices monitored by the telemetry MCP server. Each service exposes deployment logs, error telemetry, and operational runbooks.
        </p>
      </div>

      {services.length === 0 ? (
        <EmptyState
          title="No Services Found"
          description="The backend reported zero services. Ensure the telemetry server is configured with mock operational services."
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
          {services.map((svc) => (
            <div key={svc.service_name} className="card" data-testid={`service-card-${svc.service_name}`}>
              <div className="card-header" style={{ marginBottom: 14, paddingBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--color-navy-active)',
                      color: 'var(--color-navy)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Server size={20} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{svc.service_name}</h3>
                    {svc.description && (
                      <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                        {svc.description}
                      </p>
                    )}
                  </div>
                </div>
                <StatusBadge status={svc.status} variant="service" />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, marginBottom: 18 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 6 }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Latest Deployment:</span>
                  <span className="mono-text" style={{ fontWeight: 600 }}>
                    {svc.latest_deployment_version || 'None recorded'}
                  </span>
                </div>

                {svc.latest_deployment_time && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 6 }}>
                    <span style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={13} /> Deployed At:
                    </span>
                    <span style={{ fontSize: 12 }}>
                      {new Date(svc.latest_deployment_time).toLocaleString()}
                    </span>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 6 }}>
                  <span style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <GitBranch size={13} /> Total Releases:
                  </span>
                  <span style={{ fontWeight: 600 }}>{svc.total_deployments}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 6 }}>
                  <span style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertCircle size={13} /> Error Telemetry:
                  </span>
                  <span
                    style={{
                      fontWeight: 600,
                      color: svc.error_count > 0 ? 'var(--color-critical)' : 'var(--color-success)',
                    }}
                  >
                    {svc.error_count} recent errors
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <BookOpen size={13} /> Runbook Resource:
                  </span>
                  <span>
                    {svc.runbook_available ? (
                      <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>service://runbooks/{svc.service_name}</span>
                    ) : (
                      <span style={{ color: 'var(--color-text-muted)' }}>Not configured</span>
                    )}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  onClick={() => navigate(`/investigations?service=${encodeURIComponent(svc.service_name)}`)}
                  data-testid={`investigate-card-btn-${svc.service_name}`}
                >
                  <Sparkles size={15} />
                  <span>Investigate Service</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
