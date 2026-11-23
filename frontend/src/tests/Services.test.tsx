import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ServicesPage } from '../pages/ServicesPage';
import * as servicesApi from '../api/services';

vi.mock('../api/services');

describe('ServicesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders all operational services with runbook links and investigation buttons', async () => {
    vi.mocked(servicesApi.fetchServices).mockResolvedValue([
      {
        service_name: 'auth-service',
        status: 'healthy',
        runbook_available: true,
        total_deployments: 8,
        error_count: 0,
        latest_deployment_version: 'v2.1.0',
        latest_deployment_time: '2026-11-20T09:00:00Z',
        description: 'Authentication and session tokens',
      },
      {
        service_name: 'payments-api',
        status: 'degraded',
        runbook_available: true,
        total_deployments: 5,
        error_count: 12,
        latest_deployment_version: 'v1.4.2',
        latest_deployment_time: '2026-11-20T10:00:00Z',
        description: 'Payment checkout gateway',
      },
    ]);

    render(
      <MemoryRouter>
        <ServicesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('services-page')).toBeInTheDocument();
      expect(screen.getByTestId('service-card-auth-service')).toBeInTheDocument();
      expect(screen.getByTestId('service-card-payments-api')).toBeInTheDocument();
    });

    expect(screen.getByTestId('investigate-card-btn-auth-service')).toBeInTheDocument();
    expect(screen.getByTestId('investigate-card-btn-payments-api')).toBeInTheDocument();
  });
});
