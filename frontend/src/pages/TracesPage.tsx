import React, { useEffect, useState, useCallback } from 'react';
import { Activity, Filter } from 'lucide-react';
import { fetchTraces } from '../api/traces';
import { TraceResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/common/EmptyState';
import { useLayout } from '../components/layout/AppLayout';
import { getErrorMessage } from '../api/client';

export const TracesPage: React.FC = () => {
  const { refreshCount } = useLayout();

  const [traces, setTraces] = useState<TraceResponse[]>([]);
  const [runIdFilter, setRunIdFilter] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadTraces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTraces({
        run_id: activeFilter.trim() || undefined,
      });
      setTraces(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [activeFilter]);

  useEffect(() => {
    loadTraces();
  }, [loadTraces, refreshCount]);

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveFilter(runIdFilter.trim());
  };

  const handleClearFilter = () => {
    setRunIdFilter('');
    setActiveFilter('');
  };

  return (
    <div className="traces-page" data-testid="traces-page">
      {error && <ErrorBanner message={error} onRetry={loadTraces} />}

      {/* Filter by Run ID */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <form onSubmit={handleApplyFilter} style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={16} color="var(--color-text-secondary)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Filter by Run ID:</span>
          </div>

          <div style={{ flex: 1, minWidth: 260 }}>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. run-20261123-091522 or inv-101"
              value={runIdFilter}
              onChange={(e) => setRunIdFilter(e.target.value)}
              aria-label="Filter traces by run ID"
              data-testid="filter-run-id-input"
            />
          </div>

          <button type="submit" className="btn btn-secondary btn-sm" data-testid="apply-filter-btn">
            Apply Filter
          </button>

          {activeFilter && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={handleClearFilter}>
              Clear
            </button>
          )}

          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-text-secondary)' }}>
            Showing <strong>{traces.length}</strong> trace events
          </div>
        </form>
      </div>

      {loading ? (
        <LoadingSpinner message="Retrieving sanitized execution traces from JSONL logs..." />
      ) : traces.length === 0 ? (
        <EmptyState
          title="No Execution Traces"
          description={
            activeFilter
              ? `No trace events found matching Run ID "${activeFilter}".`
              : 'Zero traces currently recorded in the traces directory. Run an investigation to generate traces.'
          }
          icon={<Activity size={44} />}
        />
      ) : (
        <div className="table-container">
          <table className="data-table" data-testid="traces-table">
            <thead>
              <tr>
                <th style={{ width: 170 }}>Timestamp</th>
                <th style={{ width: 180 }}>Run ID</th>
                <th style={{ width: 200 }}>Tool</th>
                <th style={{ width: 120 }}>Server</th>
                <th style={{ width: 100 }}>Duration</th>
                <th style={{ width: 90 }}>Status</th>
                <th>Arguments</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((trace, idx) => (
                <tr key={`${trace.run_id}-${idx}`} data-testid={`trace-row-${idx}`}>
                  <td className="mono-text" style={{ fontSize: 11.5, color: 'var(--color-text-secondary)' }}>
                    {trace.timestamp}
                  </td>
                  <td className="mono-text" style={{ fontWeight: 600, color: 'var(--color-navy)', fontSize: 12 }}>
                    {trace.run_id}
                  </td>
                  <td>
                    <span className="mono-text" style={{ fontWeight: 600, color: 'var(--color-orange)' }}>
                      {trace.tool}
                    </span>
                  </td>
                  <td>
                    <span
                      style={{
                        fontSize: 11,
                        padding: '2px 6px',
                        backgroundColor: '#f1f5f9',
                        borderRadius: 4,
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {trace.mcp_server || 'telemetry'}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, fontWeight: 500 }}>
                    {trace.duration_ms.toFixed(1)} ms
                  </td>
                  <td>
                    <StatusBadge status={trace.status} variant="trace" />
                  </td>
                  <td>
                    <details style={{ fontSize: 11, cursor: 'pointer' }}>
                      <summary style={{ color: 'var(--color-navy)', outline: 'none' }}>
                        View inputs
                      </summary>
                      <pre
                        style={{
                          marginTop: 4,
                          padding: 8,
                          backgroundColor: '#1e293b',
                          color: '#f8fafc',
                          borderRadius: 4,
                          overflowX: 'auto',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 11,
                        }}
                      >
                        {JSON.stringify(trace.arguments, null, 2)}
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
  );
};
