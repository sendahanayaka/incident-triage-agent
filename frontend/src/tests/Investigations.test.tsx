import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { InvestigationsPage } from '../pages/InvestigationsPage';
import * as investigationsApi from '../api/investigations';
import * as servicesApi from '../api/services';

vi.mock('../api/investigations');
vi.mock('../api/services');

describe('InvestigationsPage', () => {
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

  it('renders investigation form with quick scenario buttons', async () => {
    render(
      <MemoryRouter>
        <InvestigationsPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('investigation-form')).toBeInTheDocument();
    expect(screen.getByTestId('investigation-input')).toBeInTheDocument();
    expect(screen.getByText('Payments API Triage')).toBeInTheDocument();
    expect(screen.getByTestId('start-investigation-btn')).toBeDisabled();
  });

  it('fills query and submits investigation, displaying synthesized results and tool timeline', async () => {
    vi.mocked(investigationsApi.startInvestigation).mockResolvedValue({
      id: 'inv-test-77',
      query: 'Investigate payments-api high error rates',
      status: 'completed',
      findings: 'The payments-api is failing due to downstream gateway timeout in commit c8f7d9a1.',
      evidence: [
        'LOG-037: 504 Gateway Timeout on /v1/charges',
        'Deployment pay-204 updated timeout from 30s to 5s',
      ],
      recommendations: [
        'Roll back deployment pay-204 to version v1.4.1',
        'Restore gateway timeout threshold to 30s',
      ],
      tool_calls: [
        {
          tool: 'telemetry__search_logs',
          arguments: { service: 'payments-api', severity: 'ERROR' },
          status: 'ok',
          duration_ms: 12.4,
        },
      ],
      created_at: '2026-11-20T10:00:00Z',
      completed_at: '2026-11-20T10:00:05Z',
    });

    render(
      <MemoryRouter>
        <InvestigationsPage />
      </MemoryRouter>
    );

    const input = screen.getByTestId('investigation-input');
    fireEvent.change(input, { target: { value: 'Investigate payments-api high error rates' } });

    const submitBtn = screen.getByTestId('start-investigation-btn');
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId('investigation-result')).toBeInTheDocument();
    });

    expect(screen.getByTestId('findings-section')).toHaveTextContent(/downstream gateway timeout/i);
    expect(screen.getByTestId('evidence-section')).toHaveTextContent(/LOG-037/i);
    expect(screen.getByTestId('recommendations-section')).toHaveTextContent(/Roll back deployment/i);
    expect(screen.getByTestId('tool-calls-section')).toHaveTextContent(/telemetry__search_logs/i);
  });
});
