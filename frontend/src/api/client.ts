import axios, { AxiosError } from 'axios';

// Default to '/api' which Vite proxies to backend, or explicit VITE_API_BASE_URL
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // Live LLM multi-step agent investigations can take 30-90s
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string | { message?: string } }>;
    if (axiosError.response?.data?.detail) {
      const detail = axiosError.response.data.detail;
      return typeof detail === 'string' ? detail : JSON.stringify(detail);
    }
    if (axiosError.code === 'ERR_NETWORK') {
      return 'Backend service is unavailable. Please ensure FastAPI server is running on http://localhost:8000.';
    }
    return axiosError.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred.';
}
