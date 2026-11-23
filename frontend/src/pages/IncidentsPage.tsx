import React, { useEffect, useState, useCallback } from 'react';
import { AlertOctagon, User, Clock, Info } from 'lucide-react';
import { fetchIncidents } from '../api/incidents';
import { IncidentResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const IncidentsPage: React.FC = () => {
  const { refreshCount } = useLayout();

  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadIncidents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchIncidents();
      setIncidents(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents, refreshCount]);

  if (loading) {
    return <LoadingSpinner message="Retrieving persisted incidents from SQLite database..." />;
  }

  return (
    <div className="incidents-page" data-testid="incidents-page">
      {error && <ErrorBanner message={error} onRetry={loadIncidents} />}

      <div
        style={{
          backgroundColor: '#eff6ff',
          borderLeft: '4px solid var(--color-info)',
          padding: '12px 18px',
          marginBottom: 20,
          borderRadius: '0 var(--radius-md) var(--radius-md) 0',
          fontSize: 13,
          color: '#1e40af',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <Info size={18} style={{ flexShrink: 0 }} />
        <span>
          Incident tickets are persisted in SQLite (<code>database/schema.sql</code>). Tickets cannot be created automatically without human operator approval through the agent approval gate.
        </span>
      </div>

      {incidents.length === 0 ? (
        <EmptyState
          title="No Persisted Incidents"
          description="There are currently no incident tickets stored in the SQLite database."
          icon={<AlertOctagon size={44} />}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {incidents.map((incident) => (
            <div
              key={incident.ticket_id}
              className="card"
              data-testid={`incident-card-${incident.ticket_id}`}
              style={{ borderLeft: incident.severity === 'CRITICAL' ? '4px solid var(--color-critical)' : '4px solid var(--color-orange)' }}
            >
              <div className="card-header" style={{ marginBottom: 12, paddingBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span className="mono-text" style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-navy)' }}>
                    {incident.ticket_id}
                  </span>
                  <StatusBadge status={incident.severity} variant="severity" />
                  <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{incident.title}</h3>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12, color: 'var(--color-text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <User size={13} /> {incident.assignee}
                  </span>
                  {incident.created_at && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={13} /> {new Date(incident.created_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>

              <div
                style={{
                  fontSize: 13.5,
                  lineHeight: 1.6,
                  color: 'var(--color-text)',
                  backgroundColor: '#f8fafc',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                {incident.summary}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
