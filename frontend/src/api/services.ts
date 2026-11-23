import { apiClient } from './client';
import { ServiceResponse } from '../types/api';

export async function fetchServices(): Promise<ServiceResponse[]> {
  const response = await apiClient.get<ServiceResponse[]>('/services');
  return response.data;
}
