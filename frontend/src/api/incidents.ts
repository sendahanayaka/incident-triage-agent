import { apiClient } from './client';
import { IncidentResponse } from '../types/api';

export async function fetchIncidents(): Promise<IncidentResponse[]> {
  const response = await apiClient.get<IncidentResponse[]>('/incidents');
  return response.data;
}
