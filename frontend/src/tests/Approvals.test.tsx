import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ApprovalsPage } from '../pages/ApprovalsPage';
import * as approvalsApi from '../api/approvals';

vi.mock('../api/approvals');

describe('ApprovalsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders pending approvals and requires confirmation modal before approving', async () => {
    vi.mocked(approvalsApi.fetchPendingApprovals).mockResolvedValue([
      {
        id: 'app-501',
        action_type: 'create_incident_ticket',
        description: 'Create incident ticket for payments outage',
        parameters: { title: 'Payments Outage', severity: 'CRITICAL', assignee: 'oncall' },
        risk_level: 'CRITICAL',
        status: 'pending',
        created_at: '2026-11-20T10:15:00Z',
        requested_by: 'agent',
        decision_at: null,
        decision_by: null,
        execution_status: 'pending',
        execution_result: null,
      },
    ]);

    render(
      <MemoryRouter>
        <ApprovalsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('approval-card-app-501')).toBeInTheDocument();
    });

    expect(screen.getAllByText('create_incident_ticket').length).toBeGreaterThanOrEqual(1);

    // Click Approve button to open modal
    const approveBtn = screen.getByTestId('approve-btn-app-501');
    fireEvent.click(approveBtn);

    expect(screen.getByTestId('approval-modal')).toBeInTheDocument();
    expect(screen.getByText(/Confirm Action Approval/i)).toBeInTheDocument();

    // Mock approval execution
    vi.mocked(approvalsApi.approvePendingAction).mockResolvedValue({
      approval_id: 'app-501',
      status: 'approved',
      action_type: 'create_incident_ticket',
      execution_status: 'executed',
      execution_result: { ticket_id: 'INC-1043' },
      message: 'Created incident ticket INC-1043 successfully.',
    });

    const confirmBtn = screen.getByTestId('modal-confirm-btn');
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(approvalsApi.approvePendingAction).toHaveBeenCalledWith('app-501', {
        operator: 'operator',
        note: undefined,
      });
    });
  });
});
