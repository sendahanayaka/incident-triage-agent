import React from 'react';
import { WifiOff } from 'lucide-react';

interface BackendAlertProps {
  isAvailable: boolean;
  message?: string;
  onRefresh?: () => void;
}

export const BackendAlert: React.FC<BackendAlertProps> = ({
  isAvailable,
  message,
  onRefresh,
}) => {
  if (isAvailable) return null;

  return (
    <div
      style={{
        backgroundColor: '#fff7ed',
        borderLeft: '4px solid var(--color-orange)',
        padding: '12px 18px',
        marginBottom: 20,
        borderRadius: '0 var(--radius-md) var(--radius-md) 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
      }}
      data-testid="backend-unavailable-alert"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <WifiOff size={18} color="var(--color-orange)" />
        <span style={{ fontSize: 13, color: '#9a3412', fontWeight: 500 }}>
          {message || 'Cannot reach FastAPI backend at http://localhost:8000. Start backend to view live data.'}
        </span>
      </div>
      {onRefresh && (
        <button
          onClick={onRefresh}
          className="btn btn-secondary btn-sm"
          style={{ fontSize: 12, padding: '4px 10px' }}
        >
          Check Connection
        </button>
      )}
    </div>
  );
};
