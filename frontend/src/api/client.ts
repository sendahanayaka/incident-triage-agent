import axios, { AxiosError } from 'axios';

// Default to http://localhost:8000/api if VITE_API_BASE_URL is not set
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000, // Agent investigations can take 15-30s
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
