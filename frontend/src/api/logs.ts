import { apiClient } from './client';
import { LogEntryResponse } from '../types/api';

export interface GetLogsParams {
  service?: string;
  severity?: string;
  limit?: number;
}

export async function fetchLogs(params: GetLogsParams = {}): Promise<LogEntryResponse[]> {
  const queryParams: Record<string, string | number> = {};
  if (params.service) queryParams.service = params.service;
  if (params.severity) queryParams.severity = params.severity;
  if (params.limit) queryParams.limit = params.limit;

  const response = await apiClient.get<LogEntryResponse[]>('/logs', {
    params: queryParams,
  });
  return response.data;
}
