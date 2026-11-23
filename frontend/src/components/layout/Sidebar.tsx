import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Server,
  Sparkles,
  AlertOctagon,
  FileText,
  GitBranch,
  ShieldCheck,
  Activity,
  Terminal,
} from 'lucide-react';
import { HealthResponse } from '../../types/api';

interface SidebarProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  isOpen: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  health,
  healthLoading,
  isOpen,
  onCloseMobile,
}) => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { to: '/services', label: 'Services', icon: <Server size={18} /> },
    { to: '/investigations', label: 'Investigations', icon: <Sparkles size={18} /> },
    { to: '/incidents', label: 'Incidents', icon: <AlertOctagon size={18} /> },
    { to: '/approvals', label: 'HITL Approvals', icon: <ShieldCheck size={18} /> },
    { to: '/logs', label: 'Telemetry Logs', icon: <FileText size={18} /> },
    { to: '/deployments', label: 'Deployments', icon: <GitBranch size={18} /> },
    { to: '/traces', label: 'Agent Traces', icon: <Activity size={18} /> },
  ];

  const isHealthy = health?.status === 'healthy';

  return (
    <aside
      className="sidebar"
      style={{
        transform: isOpen ? 'translateX(0)' : undefined,
      }}
      data-testid="app-sidebar"
    >
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <Terminal size={18} />
        </div>
        <div className="sidebar-title">
          <h1>Incident Triage Agent</h1>
          <p>Release Readiness & Ops AI</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            onClick={onCloseMobile}
            data-testid={`nav-link-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Backend API
            </div>
            <div style={{ fontSize: 12, color: '#ffffff', fontWeight: 600, marginTop: 2 }}>
              {healthLoading ? 'Connecting...' : health ? `v${health.version}` : 'Disconnected'}
            </div>
          </div>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '2px 8px',
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 600,
              backgroundColor: isHealthy ? 'rgba(5, 150, 105, 0.2)' : 'rgba(220, 38, 38, 0.2)',
              color: isHealthy ? '#34d399' : '#f87171',
              border: `1px solid ${isHealthy ? 'rgba(5, 150, 105, 0.4)' : 'rgba(220, 38, 38, 0.4)'}`,
            }}
            data-testid="backend-status-pill"
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: isHealthy ? '#10b981' : '#ef4444',
              }}
            />
            {isHealthy ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </aside>
  );
};
