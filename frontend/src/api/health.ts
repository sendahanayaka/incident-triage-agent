import { apiClient } from './client';
import { HealthResponse } from '../types/api';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}
