import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'service' | 'severity' | 'approval' | 'deployment' | 'trace';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normalized = (status || '').toLowerCase().trim();

  let badgeClass = 'badge-neutral';

  if (['healthy', 'ok', 'completed', 'approved', 'deployed', 'active'].includes(normalized)) {
    badgeClass = 'badge-healthy';
  } else if (['degraded', 'warn', 'warning', 'pending', 'medium'].includes(normalized)) {
    badgeClass = 'badge-warn';
  } else if (['critical', 'error', 'fatal', 'rejected', 'failed', 'high'].includes(normalized)) {
    badgeClass = 'badge-critical';
  } else if (['info', 'in_progress', 'running'].includes(normalized)) {
    badgeClass = 'badge-info';
  }

  // Display label formatting
  const displayLabel = status ? status.toUpperCase() : 'UNKNOWN';

  return (
    <span className={`badge ${badgeClass}`} data-testid={`status-badge-${normalized}`}>
      <span className="badge-dot" />
      <span>{displayLabel}</span>
    </span>
  );
};
