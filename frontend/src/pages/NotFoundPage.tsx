import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px 24px',
        textAlign: 'center',
      }}
      data-testid="not-found-page"
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: '50%',
          backgroundColor: 'var(--color-critical-bg)',
          color: 'var(--color-critical)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 16,
        }}
      >
        <AlertTriangle size={32} />
      </div>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-text)', marginBottom: 8 }}>
        404 — Page Not Found
      </h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', maxWidth: 440, marginBottom: 24 }}>
        The requested operations dashboard view does not exist or has been relocated.
      </p>
      <Link to="/" className="btn btn-primary">
        <Home size={16} />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  );
};
