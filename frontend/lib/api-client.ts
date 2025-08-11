/**
 * Centralized API client for all backend communication
 * This provides a robust, type-safe interface to the backend API
 */

import { getSession } from 'next-auth/react'

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  details?: any
}

export interface UserData {
  id: string
  email: string
  name?: string
  emailVerified: boolean
  freeReportUsed: boolean
  stripeCustomerId?: string
  hasActiveSubscription: boolean
}

export interface CheckoutSessionResponse {
  checkout_url: string
}

export interface BillingPortalResponse {
  portal_url: string
}

export interface SubscriptionStatus {
  has_active_subscription: boolean
  free_report_used: boolean
  stripe_customer_id?: string
  email_verified: boolean
}

export interface SignupRequest {
  email: string
  password?: string
  name?: string
}

export interface LoginRequest {
  email: string
  password?: string
}

export interface AuthResponse {
  access_token: string
  user: UserData
}

// API Client Class
export class ApiClient {
  private baseUrl: string
  private timeout: number

  constructor(baseUrl?: string, timeout = 30000) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    this.timeout = timeout
  }

  /**
   * Get the current user's JWT token from the session
   */
  private async getAuthToken(): Promise<string | null> {
    const session = await getSession()
    return (session as any)?.accessToken || null
  }

  /**
   * Make an authenticated API request
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = await this.getAuthToken()
    
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeout)

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
          ...options.headers,
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type')
      if (!contentType?.includes('application/json')) {
        if (!response.ok) {
          throw new ApiError(`Request failed: ${response.statusText}`, response.status)
        }
        return {} as T
      }

      const data = await response.json()

      if (!response.ok) {
        throw new ApiError(
          data.detail || data.error || `Request failed: ${response.statusText}`,
          response.status,
          data
        )
      }

      return data
    } catch (error) {
      clearTimeout(timeoutId)
      
      if (error instanceof ApiError) {
        throw error
      }
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new ApiError('Request timeout', 408)
        }
        throw new ApiError(error.message, 500)
      }
      
      throw new ApiError('Unknown error occurred', 500)
    }
  }

  // Auth Endpoints
  async signup(data: SignupRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async login(data: LoginRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getCurrentUser(): Promise<UserData> {
    return this.request<UserData>('/auth/me')
  }

  async sendVerificationEmail(email: string): Promise<{ message: string }> {
    return this.request('/auth/send-verification', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  // Billing Endpoints
  async createCheckoutSession(): Promise<CheckoutSessionResponse> {
    return this.request<CheckoutSessionResponse>('/api/v1/billing/checkout', {
      method: 'POST',
    })
  }

  async createBillingPortalSession(): Promise<BillingPortalResponse> {
    return this.request<BillingPortalResponse>('/api/v1/billing/billing-portal', {
      method: 'POST',
    })
  }

  async getSubscriptionStatus(): Promise<SubscriptionStatus> {
    return this.request<SubscriptionStatus>('/api/v1/billing/subscription-status')
  }

  // Blueprint/Job Endpoints
  async uploadBlueprint(formData: FormData): Promise<any> {
    const token = await this.getAuthToken()
    
    const response = await fetch(`${this.baseUrl}/api/v1/blueprint/upload`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new ApiError(error.detail || 'Upload failed', response.status, error)
    }

    return response.json()
  }

  async getJob(jobId: string): Promise<any> {
    return this.request(`/api/v1/job/${jobId}`)
  }

  async getJobStatus(jobId: string): Promise<any> {
    return this.request(`/api/v1/job/${jobId}/status`)
  }

  async downloadReport(jobId: string): Promise<Blob> {
    const token = await this.getAuthToken()
    
    const response = await fetch(`${this.baseUrl}/api/v1/job/${jobId}/download`, {
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    })

    if (!response.ok) {
      throw new ApiError('Download failed', response.status)
    }

    return response.blob()
  }

  // User Endpoints
  async getUserProjects(limit = 10, offset = 0): Promise<any> {
    return this.request(`/api/v1/jobs/user?limit=${limit}&offset=${offset}`)
  }
}

// Custom Error Class
export class ApiError extends Error {
  public status: number
  public details?: any

  constructor(message: string, status: number, details?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }

  isAuthError(): boolean {
    return this.status === 401 || this.status === 403
  }

  isPaymentRequired(): boolean {
    return this.status === 402
  }

  isNotFound(): boolean {
    return this.status === 404
  }

  isServerError(): boolean {
    return this.status >= 500
  }

  isNetworkError(): boolean {
    return this.status === 0 || this.status === 408
  }
}

// Singleton instance
export const apiClient = new ApiClient()

// React Hook for API calls with loading and error states
import { useState, useCallback } from 'react'

export function useApiCall<T = any>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [data, setData] = useState<T | null>(null)

  const execute = useCallback(async (apiCall: Promise<T>) => {
    setLoading(true)
    setError(null)
    
    try {
      const result = await apiCall
      setData(result)
      return result
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('Unknown error', 500)
      setError(apiError)
      throw apiError
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setLoading(false)
  }, [])

  return { execute, loading, error, data, reset }
}