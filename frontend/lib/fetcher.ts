import axios from 'axios'
import { API_URL } from '../constants/api'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data)
    
    // Handle specific error cases
    if (error.response?.status === 403 && error.response?.headers?.['x-verification-required']) {
      // Email verification required
      throw new EmailVerificationError(error.response.data.detail)
    }
    
    if (error.response?.status === 402 && error.response?.headers?.['x-checkout-url']) {
      // Payment required - redirect to Stripe
      throw new PaymentRequiredError(error.response.data.detail, error.response.headers['x-checkout-url'])
    }
    
    return Promise.reject(error)
  }
)

// Custom error classes
export class EmailVerificationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'EmailVerificationError'
  }
}

export class PaymentRequiredError extends Error {
  public checkoutUrl: string
  
  constructor(message: string, checkoutUrl: string) {
    super(message)
    this.name = 'PaymentRequiredError'
    this.checkoutUrl = checkoutUrl
  }
}

// API fetch with better error handling
export async function apiFetch(url: string, opts: RequestInit = {}) {
  const resp = await fetch(url, opts);
  const txt = await resp.text();
  if (!resp.ok) {
    console.error("🛑 Backend error", resp.status, txt);
    throw new Error(`API ${resp.status}: ${txt}`);
  }
  return JSON.parse(txt || "{}");
}

// SWR fetcher function
export const fetcher = async (url: string): Promise<any> => {
  const response = await api.get(url)
  return response.data
}

// Fetcher with POST data
export const postFetcher = async ({ url, data }: { url: string; data: any }): Promise<any> => {
  const response = await api.post(url, data)
  return response.data
}

// API helper functions
export const apiHelpers = {
  // User projects
  getUserProjects: (email: string, limit?: number) => {
    const params = new URLSearchParams({ email })
    if (limit) params.append('limit', limit.toString())
    return fetcher(`/api/v1/jobs/list?${params.toString()}`)
  },
  
  // Job status
  getJobStatus: (jobId: string) => fetcher(`/api/job/${jobId}`),
  
  // Project details
  getProjectDetails: (projectId: string, email: string) => {
    const params = new URLSearchParams({ email })
    return fetcher(`/api/v1/jobs/${projectId}/details?${params.toString()}`)
  },
  
  // Email verification
  sendVerificationEmail: (email: string) => 
    postFetcher({ url: '/api/v1/auth/send-verification', data: { email } }),
  
  checkVerificationStatus: (email: string) => 
    fetcher(`/api/v1/auth/verify-status/${encodeURIComponent(email)}`),
  
  // File upload
  uploadBlueprint: async (formData: FormData) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const response = await fetch(`${apiBase}/api/v1/blueprint/upload`, {
        method: 'POST',
        body: formData,
      });
      const text = await response.text();
      if (!response.ok) {
        console.error(`Upload failed: ${response.status}`, text);
        throw new Error(`API ${response.status}: ${text}`);
      }
      return JSON.parse(text);
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  },
  
  // Subscription
  createSubscription: (email: string) =>
    postFetcher({ url: '/api/v1/subscribe', data: { email } }),
}

// Download helper (doesn't use SWR since it's a file download)
export const downloadProjectReport = async (projectId: string, email: string) => {
  const params = new URLSearchParams({ email })
  const response = await api.get(`/api/v1/jobs/${projectId}/download?${params.toString()}`, {
    responseType: 'blob',
  })
  
  // Create download link
  const blob = new Blob([response.data], { type: 'application/pdf' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  
  // Get filename from response headers
  const contentDisposition = response.headers['content-disposition']
  let filename = 'report.pdf'
  if (contentDisposition) {
    const matches = /filename="([^"]*)"/.exec(contentDisposition)
    if (matches) filename = matches[1]
  }
  
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export default api