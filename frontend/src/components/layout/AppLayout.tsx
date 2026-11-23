import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { fetchHealth } from '../../api/health';
import { HealthResponse } from '../../types/api';
import { BackendAlert } from '../common/BackendAlert';

interface LayoutContextType {
  triggerRefresh: () => void;
  refreshCount: number;
  health: HealthResponse | null;
  isBackendAvailable: boolean;
}

const LayoutContext = createContext<LayoutContextType>({
  triggerRefresh: () => {},
  refreshCount: 0,
  health: null,
  isBackendAvailable: false,
});

export const useLayout = () => useContext(LayoutContext);

export const AppLayout: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [refreshCount, setRefreshCount] = useState<number>(0);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const location = useLocation();

  const loadHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 30000); // 30s background poll
    return () => clearInterval(interval);
  }, [loadHealth]);

  const triggerRefresh = useCallback(() => {
    setRefreshCount((prev) => prev + 1);
    loadHealth();
  }, [loadHealth]);

  const getPageMeta = (pathname: string) => {
    switch (pathname) {
      case '/':
        return { title: 'Operational Dashboard', subtitle: 'Real-time telemetry, service health, and active incidents' };
      case '/services':
        return { title: 'Service Directory', subtitle: 'Monitored microservices, runbooks, and deployment status' };
      case '/investigations':
        return { title: 'Incident Investigations', subtitle: 'AI-assisted root cause analysis and release readiness checks' };
      case '/incidents':
        return { title: 'Incident Tickets', subtitle: 'Persisted operational incidents in SQLite database' };
      case '/approvals':
        return { title: 'Human-in-the-Loop Approvals', subtitle: 'Operator authorization gate for mutation actions' };
      case '/logs':
        return { title: 'Telemetry Logs', subtitle: 'Operational event logs queryable by service and severity' };
      case '/deployments':
        return { title: 'Deployment History', subtitle: 'Release history, commit hashes, and rollback statuses' };
      case '/traces':
        return { title: 'Agent Execution Traces', subtitle: 'Sanitized JSONL tool invocation and duration logs' };
      default:
        return { title: 'Incident Triage & Release Readiness', subtitle: 'Autonomous AI Operations' };
    }
  };

  const pageMeta = getPageMeta(location.pathname);

  return (
    <LayoutContext.Provider
      value={{
        triggerRefresh,
        refreshCount,
        health,
        isBackendAvailable: health?.status === 'healthy',
      }}
    >
      <div className="app-container">
        <Sidebar
          health={health}
          healthLoading={healthLoading}
          isOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />

        <div className="main-layout">
          <Header
            title={pageMeta.title}
            subtitle={pageMeta.subtitle}
            health={health}
            loading={healthLoading}
            onRefresh={triggerRefresh}
            onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          />

          <main className="main-content">
            <BackendAlert
              isAvailable={health?.status === 'healthy'}
              onRefresh={loadHealth}
            />
            <Outlet />
          </main>
        </div>
      </div>
    </LayoutContext.Provider>
  );
};
