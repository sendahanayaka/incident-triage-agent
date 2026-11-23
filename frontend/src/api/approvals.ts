import { apiClient } from './client';
import {
  ApprovalDecisionRequest,
  ApprovalDecisionResponse,
  ApprovalResponse,
} from '../types/api';

export async function fetchPendingApprovals(): Promise<ApprovalResponse[]> {
  const response = await apiClient.get<ApprovalResponse[]>('/approvals/pending');
  return response.data;
}

export async function approvePendingAction(
  id: string,
  request?: ApprovalDecisionRequest
): Promise<ApprovalDecisionResponse> {
  const response = await apiClient.post<ApprovalDecisionResponse>(
    `/approvals/${encodeURIComponent(id)}/approve`,
    request || { operator: 'operator' }
  );
  return response.data;
}

export async function rejectPendingAction(
  id: string,
  request?: ApprovalDecisionRequest
): Promise<ApprovalDecisionResponse> {
  const response = await apiClient.post<ApprovalDecisionResponse>(
    `/approvals/${encodeURIComponent(id)}/reject`,
    request || { operator: 'operator' }
  );
  return response.data;
}
