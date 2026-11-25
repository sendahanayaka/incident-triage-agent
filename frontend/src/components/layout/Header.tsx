import React from 'react';
import { RefreshCw, Menu, Wifi, WifiOff, Cpu } from 'lucide-react';
import { HealthResponse } from '../../types/api';

interface HeaderProps {
  title: string;
  subtitle?: string;
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
  onToggleMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  health,
  loading,
  onRefresh,
  onToggleMobileMenu,
}) => {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="app-header" data-testid="app-header">
      <div className="header-left">
        <button
          className="mobile-menu-btn"
          onClick={onToggleMobileMenu}
          aria-label="Toggle Navigation Menu"
        >
          <Menu size={20} />
        </button>
        <div className="page-title-group">
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>

      <div className="header-actions">
        {health?.llm && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 12,
              color: health.llm.mode === 'live' ? '#2563eb' : '#7c3aed',
              backgroundColor: health.llm.mode === 'live' ? '#eff6ff' : '#f5f3ff',
              padding: '4px 10px',
              borderRadius: 16,
              border: `1px solid ${health.llm.mode === 'live' ? '#bfdbfe' : '#ddd6fe'}`,
              fontWeight: 500,
            }}
            data-testid="header-llm-indicator"
            title={`Model: ${health.llm.model} | Base URL: ${health.llm.base_url} | API Key: ${health.llm.has_api_key ? 'Configured' : 'Offline (No Key Required)'}`}
          >
            <Cpu size={14} />
            <span>LLM: {health.llm.mode.toUpperCase()} ({health.llm.provider})</span>
          </div>
        )}

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12,
            color: isHealthy ? 'var(--color-success)' : 'var(--color-critical)',
            backgroundColor: isHealthy ? 'var(--color-success-bg)' : 'var(--color-critical-bg)',
            padding: '4px 10px',
            borderRadius: 16,
            border: `1px solid ${isHealthy ? 'var(--color-success-border)' : 'var(--color-critical-border)'}`,
            fontWeight: 500,
          }}
          data-testid="header-connectivity-indicator"
        >
          {isHealthy ? <Wifi size={14} /> : <WifiOff size={14} />}
          <span>{isHealthy ? 'FastAPI Connected' : 'FastAPI Offline'}</span>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          disabled={loading}
          data-testid="header-refresh-button"
          title="Refresh current page data"
        >
          <RefreshCw size={14} className={loading ? 'spinner' : ''} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
};
