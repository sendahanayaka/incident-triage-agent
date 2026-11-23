import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import * as healthApi from '../api/health';
import * as servicesApi from '../api/services';
import * as incidentsApi from '../api/incidents';
import * as deploymentsApi from '../api/deployments';
import * as approvalsApi from '../api/approvals';

vi.mock('../api/health');
vi.mock('../api/services');
vi.mock('../api/incidents');
vi.mock('../api/deployments');
vi.mock('../api/approvals');

describe('Application Shell & Navigation', () => {
  it('renders sidebar with all navigation links and header connectivity', async () => {
    vi.mocked(healthApi.fetchHealth).mockResolvedValue({
      status: 'healthy',
      application: 'IncidentTriageAgent',
      version: '1.0.0',
      environment: 'development',
    });
    vi.mocked(servicesApi.fetchServices).mockResolvedValue([]);
    vi.mocked(incidentsApi.fetchIncidents).mockResolvedValue([]);
    vi.mocked(deploymentsApi.fetchDeployments).mockResolvedValue([]);
    vi.mocked(approvalsApi.fetchPendingApprovals).mockResolvedValue([]);

    render(<App />);

    expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();

    // Verify all primary navigation links
    expect(screen.getByTestId('nav-link-dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-services')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-investigations')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-incidents')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-hitl-approvals')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-telemetry-logs')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-deployments')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-agent-traces')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('header-connectivity-indicator')).toHaveTextContent(/FastAPI Connected/i);
      expect(screen.getByTestId('backend-status-pill')).toHaveTextContent(/ONLINE/i);
    });
  });
});
