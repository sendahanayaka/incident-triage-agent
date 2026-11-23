import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../pages/DashboardPage';
import * as servicesApi from '../api/services';
import * as incidentsApi from '../api/incidents';
import * as deploymentsApi from '../api/deployments';
import * as approvalsApi from '../api/approvals';

vi.mock('../api/services');
vi.mock('../api/incidents');
vi.mock('../api/deployments');
vi.mock('../api/approvals');

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders operational metrics and services table with live backend data', async () => {
    vi.mocked(servicesApi.fetchServices).mockResolvedValue([
      {
        service_name: 'payments-api',
        status: 'degraded',
        runbook_available: true,
        total_deployments: 5,
        error_count: 14,
        latest_deployment_version: 'v1.4.2',
        latest_deployment_time: '2026-11-20T10:00:00Z',
        description: 'Core payment processing service',
      },
    ]);
    vi.mocked(incidentsApi.fetchIncidents).mockResolvedValue([
      {
        ticket_id: 'INC-1042',
        title: 'Payment Gateway Connection Timeout',
        severity: 'CRITICAL',
        summary: 'Elevated 500 error rates on /charge endpoint',
        assignee: 'payments-oncall',
        created_at: '2026-11-20T10:30:00Z',
      },
    ]);
    vi.mocked(deploymentsApi.fetchDeployments).mockResolvedValue([
      {
        deployment_id: 'pay-204',
        service_name: 'payments-api',
        version: 'v1.4.2',
        commit_hash: 'c8f7d9a1',
        timestamp: '2026-11-20T10:00:00Z',
        status: 'deployed',
        rollback_status: 'not_requested',
        summary: 'Update database retry timeout',
      },
    ]);
    vi.mocked(approvalsApi.fetchPendingApprovals).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    // Initial loading state
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

    // Wait for loaded content
    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    // Check metric cards
    expect(screen.getByTestId('metric-services')).toHaveTextContent('1');
    expect(screen.getByTestId('metric-incidents')).toHaveTextContent('1');

    // Check service row
    expect(screen.getByTestId('service-row-payments-api')).toBeInTheDocument();
    expect(screen.getAllByText('payments-api').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('INC-1042')).toBeInTheDocument();
    expect(screen.getByText('pay-204')).toBeInTheDocument();
  });

  it('renders pending HITL approval banner when mutation proposals are queued', async () => {
    vi.mocked(servicesApi.fetchServices).mockResolvedValue([]);
    vi.mocked(incidentsApi.fetchIncidents).mockResolvedValue([]);
    vi.mocked(deploymentsApi.fetchDeployments).mockResolvedValue([]);
    vi.mocked(approvalsApi.fetchPendingApprovals).mockResolvedValue([
      {
        id: 'app-991',
        action_type: 'create_incident_ticket',
        description: 'Create P1 ticket for payments degradation',
        parameters: { title: 'Payments 500 Spike', severity: 'CRITICAL' },
        risk_level: 'CRITICAL',
        status: 'pending',
        created_at: '2026-11-20T10:35:00Z',
        requested_by: 'agent',
        decision_at: null,
        decision_by: null,
        execution_status: 'pending',
        execution_result: null,
      },
    ]);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('pending-approvals-banner')).toBeInTheDocument();
    });

    expect(screen.getByText(/1 Mutation Action Awaiting Human-in-the-Loop Review/i)).toBeInTheDocument();
  });

  it('handles backend API failure gracefully with error banner', async () => {
    vi.mocked(servicesApi.fetchServices).mockRejectedValue(new Error('Connection refused'));
    vi.mocked(incidentsApi.fetchIncidents).mockResolvedValue([]);
    vi.mocked(deploymentsApi.fetchDeployments).mockResolvedValue([]);
    vi.mocked(approvalsApi.fetchPendingApprovals).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeInTheDocument();
    });

    expect(screen.getByText(/Connection refused/i)).toBeInTheDocument();
  });
});
