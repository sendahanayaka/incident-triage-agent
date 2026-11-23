import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LogsPage } from '../pages/LogsPage';
import * as logsApi from '../api/logs';
import * as servicesApi from '../api/services';

vi.mock('../api/logs');
vi.mock('../api/services');

describe('LogsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(servicesApi.fetchServices).mockResolvedValue([
      {
        service_name: 'payments-api',
        status: 'degraded',
        runbook_available: true,
        total_deployments: 3,
        error_count: 5,
        latest_deployment_version: 'v1.4.2',
        latest_deployment_time: '2026-11-20T10:00:00Z',
        description: null,
      },
    ]);
  });

  it('renders log filter controls and tabular operational logs', async () => {
    vi.mocked(logsApi.fetchLogs).mockResolvedValue([
      {
        id: 'LOG-037',
        timestamp: '2026-11-20T10:14:22Z',
        service_name: 'payments-api',
        severity: 'ERROR',
        event: 'upstream_gateway_timeout',
        message: 'Payment provider timed out after 5000ms',
      },
    ]);

    render(
      <MemoryRouter>
        <LogsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('logs-page')).toBeInTheDocument();
      expect(screen.getByTestId('logs-table')).toBeInTheDocument();
    });

    expect(screen.getByTestId('log-row-LOG-037')).toBeInTheDocument();
    expect(screen.getByText('upstream_gateway_timeout')).toBeInTheDocument();
    expect(screen.getByText('Payment provider timed out after 5000ms')).toBeInTheDocument();
    expect(screen.getByTestId('filter-service-select')).toBeInTheDocument();
    expect(screen.getByTestId('filter-severity-select')).toBeInTheDocument();
    expect(screen.getByTestId('filter-limit-select')).toBeInTheDocument();
  });
});
