import { apiClient } from './client';
import { InvestigationDetail, InvestigationRequest, InvestigationResponse } from '../types/api';

export async function startInvestigation(request: InvestigationRequest): Promise<InvestigationResponse> {
  const response = await apiClient.post<InvestigationResponse>('/investigations', request);
  return response.data;
}

export async function fetchInvestigation(id: string): Promise<InvestigationDetail> {
  const response = await apiClient.get<InvestigationDetail>(`/investigations/${encodeURIComponent(id)}`);
  return response.data;
}
