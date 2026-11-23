import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading data...',
  size = 'md',
}) => {
  const spinnerSize = size === 'sm' ? { width: 16, height: 16 } : size === 'lg' ? { width: 32, height: 32 } : {};

  return (
    <div className="state-container" role="status" aria-live="polite" data-testid="loading-spinner">
      <div className="spinner" style={spinnerSize} />
      {message && <p className="state-description" style={{ marginTop: 12 }}>{message}</p>}
    </div>
  );
};
