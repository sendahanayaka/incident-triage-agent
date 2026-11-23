import React, { useEffect, useState, useCallback } from 'react';
import { FileText, Filter } from 'lucide-react';
import { fetchLogs } from '../api/logs';
import { fetchServices } from '../api/services';
import { LogEntryResponse, ServiceResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const LogsPage: React.FC = () => {
  const { refreshCount } = useLayout();

  const [logs, setLogs] = useState<LogEntryResponse[]>([]);
  const [services, setServices] = useState<ServiceResponse[]>([]);
  const [selectedService, setSelectedService] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('');
  const [limit, setLimit] = useState<number>(50);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load available services for filter dropdown
  useEffect(() => {
    fetchServices()
      .then((data) => setServices(data))
      .catch(() => setServices([]));
  }, []);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLogs({
        service: selectedService || undefined,
        severity: selectedSeverity || undefined,
        limit,
      });
      setLogs(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [selectedService, selectedSeverity, limit]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs, refreshCount]);

  return (
    <div className="logs-page" data-testid="logs-page">
      {error && <ErrorBanner message={error} onRetry={loadLogs} />}

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={16} color="var(--color-text-secondary)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Filters:</span>
          </div>

          {/* Service Filter */}
          <div style={{ minWidth: 180 }}>
            <select
              className="form-select"
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              aria-label="Filter by Service"
              data-testid="filter-service-select"
            >
              <option value="">All Services</option>
              {services.map((svc) => (
                <option key={svc.service_name} value={svc.service_name}>
                  {svc.service_name}
                </option>
              ))}
            </select>
          </div>

          {/* Severity Filter */}
          <div style={{ minWidth: 150 }}>
            <select
              className="form-select"
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              aria-label="Filter by Severity"
              data-testid="filter-severity-select"
            >
              <option value="">All Severities</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="ERROR">ERROR</option>
              <option value="FATAL">FATAL</option>
            </select>
          </div>

          {/* Limit Selector */}
          <div style={{ minWidth: 120 }}>
            <select
              className="form-select"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              aria-label="Log Limit"
              data-testid="filter-limit-select"
            >
              <option value={25}>25 logs</option>
              <option value={50}>50 logs</option>
              <option value={100}>100 logs</option>
              <option value={200}>200 logs</option>
            </select>
          </div>

          {(selectedService || selectedSeverity) && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSelectedService('');
                setSelectedSeverity('');
              }}
            >
              Clear Filters
            </button>
          )}

          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-text-secondary)' }}>
            Showing <strong>{logs.length}</strong> entries
          </div>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Querying telemetry logs..." />
      ) : logs.length === 0 ? (
        <EmptyState
          title="No Logs Matching Criteria"
          description="Try adjusting your service or severity filters to see matching operational logs."
          icon={<FileText size={44} />}
        />
      ) : (
        <div className="table-container">
          <table className="data-table" data-testid="logs-table">
            <thead>
              <tr>
                <th style={{ width: 180 }}>Timestamp</th>
                <th style={{ width: 100 }}>Log ID</th>
                <th style={{ width: 150 }}>Service</th>
                <th style={{ width: 90 }}>Severity</th>
                <th style={{ width: 180 }}>Event</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} data-testid={`log-row-${log.id}`}>
                  <td className="mono-text" style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                    {log.timestamp}
                  </td>
                  <td className="mono-text" style={{ fontWeight: 600 }}>{log.id}</td>
                  <td style={{ fontWeight: 600 }}>{log.service_name}</td>
                  <td>
                    <StatusBadge status={log.severity} variant="severity" />
                  </td>
                  <td>
                    <span className="mono-text" style={{ fontSize: 12, color: 'var(--color-navy)' }}>
                      {log.event}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-text)' }}>
                    {log.message}
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
