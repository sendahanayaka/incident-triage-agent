import { apiClient } from './client';
import { TraceResponse } from '../types/api';

export interface GetTracesParams {
  investigation_id?: string;
  run_id?: string;
}

export async function fetchTraces(params: GetTracesParams = {}): Promise<TraceResponse[]> {
  const queryParams: Record<string, string> = {};
  if (params.investigation_id) queryParams.investigation_id = params.investigation_id;
  if (params.run_id) queryParams.run_id = params.run_id;

  const response = await apiClient.get<TraceResponse[]>('/traces', {
    params: queryParams,
  });
  return response.data;
}
