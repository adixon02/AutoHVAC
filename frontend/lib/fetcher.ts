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

// Debug logging for production issues
console.log('🔧 API Configuration:', {
  API_URL,
  NODE_ENV: process.env.NODE_ENV,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  baseURL: api.defaults.baseURL
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
    
    if (error.response?.status === 402) {
      // Payment required - redirect to checkout
      const errorDetail = error.response?.data?.detail
      const checkoutUrl = errorDetail?.checkout_url || error.response?.headers?.['x-checkout-url']
      
      if (checkoutUrl) {
        throw new PaymentRequiredError(
          errorDetail?.message || errorDetail || 'Payment required',
          checkoutUrl
        )
      }
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

// SWR fetcher function for backend API
export const fetcher = async (url: string): Promise<any> => {
  const response = await api.get(url)
  return response.data
}

// SWR fetcher function for Next.js API routes (relative URLs)
export const nextApiFetcher = async (url: string): Promise<any> => {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
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
  
  // Job status (uses Next.js API route)
  getJobStatus: (jobId: string) => nextApiFetcher(`/api/job/${jobId}`),
  
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
      const response = await api.post('/api/v1/blueprint/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return response.data
    } catch (error) {
      // Handle specific error cases
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 403 && error.response?.headers?.['x-verification-required']) {
          throw new EmailVerificationError(error.response.data.detail)
        }
        if (error.response?.status === 402) {
          // Payment required - redirect to checkout
          const errorDetail = error.response?.data?.detail
          const checkoutUrl = errorDetail?.checkout_url || error.response?.headers?.['x-checkout-url']
          
          if (checkoutUrl) {
            throw new PaymentRequiredError(
              errorDetail?.message || errorDetail || 'Payment required',
              checkoutUrl
            )
          }
        }
        
        // Handle 500 errors that might be payment-related
        if (error.response?.status === 500) {
          const errorData = error.response?.data
          const errorDetail = errorData?.detail
          
          // Check if this is a payment-related 500 error
          if (errorDetail && (
            (typeof errorDetail === 'string' && (
              errorDetail.toLowerCase().includes('payment') ||
              errorDetail.toLowerCase().includes('stripe') ||
              errorDetail.toLowerCase().includes('checkout')
            )) ||
            (typeof errorDetail === 'object' && errorDetail.error === 'free_report_used')
          )) {
            // Convert to 402 for consistent handling
            const checkoutUrl = errorDetail.checkout_url || 'https://autohvac.ai/upgrade'
            throw new PaymentRequiredError(
              typeof errorDetail === 'object' ? errorDetail : errorDetail,
              checkoutUrl
            )
          }
        }
        
        console.error(`Upload failed: ${error.response?.status}`, error.response?.data)
        throw new Error(`API ${error.response?.status}: ${JSON.stringify(error.response?.data)}`)
      }
      console.error('Upload error:', error)
      throw error
    }
  },
  
  // Subscription
  createSubscription: (email: string) =>
    postFetcher({ url: '/api/v1/subscribe', data: { email } }),
  
  // Stripe checkout
  createCheckoutSession: (email: string) =>
    postFetcher({ url: '/api/v1/billing/subscribe', data: { email } }),
  
  // Check upload eligibility
  checkCanUpload: (email: string) =>
    fetcher(`/api/v1/blueprint/users/${encodeURIComponent(email)}/can-upload`),
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