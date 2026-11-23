import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
}) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--color-critical-bg)',
        border: '1px solid var(--color-critical-border)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 16,
      }}
      role="alert"
      data-testid="error-banner"
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <AlertCircle size={20} color="var(--color-critical)" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-critical)', margin: 0 }}>
            {title}
          </h4>
          <p style={{ fontSize: 13, color: '#991b1b', marginTop: 4, margin: 0 }}>
            {message}
          </p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn btn-secondary btn-sm"
          style={{ flexShrink: 0 }}
          data-testid="retry-button"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
};
