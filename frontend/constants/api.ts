// Centralized API configuration
export const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || `/api/${API_VERSION}`;
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'development' 
    ? 'http://localhost:8001' 
    : 'https://autohvac-backend.onrender.com');
export const USE_SMOKE_TEST = process.env.NEXT_PUBLIC_USE_SMOKE_TEST === 'true';

// API endpoints
export const API_ENDPOINTS = {
  upload: `${API_BASE}/blueprint/upload`,
  jobStatus: (jobId: string) => `${API_BASE}/blueprint/jobs/${jobId}`,
  health: '/healthz',
} as const;

// Smoke test endpoint
export const SMOKE_TEST_ENDPOINT = 'https://httpbin.org/post';

// Request timeout in milliseconds
export const REQUEST_TIMEOUT = 30000; // 30 seconds