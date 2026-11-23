import { apiClient } from './client';
import { DeploymentResponse } from '../types/api';

export interface GetDeploymentsParams {
  service?: string;
}

export async function fetchDeployments(params: GetDeploymentsParams = {}): Promise<DeploymentResponse[]> {
  const queryParams: Record<string, string> = {};
  if (params.service) queryParams.service = params.service;

  const response = await apiClient.get<DeploymentResponse[]>('/deployments', {
    params: queryParams,
  });
  return response.data;
}
