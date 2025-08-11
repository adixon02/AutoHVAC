import { NextApiRequest, NextApiResponse } from 'next'

/**
 * Signup endpoint - proxies to backend API
 * The backend handles all business logic including:
 * - Password validation and hashing
 * - Rate limiting and security
 * - User creation and email verification
 * - Stripe customer creation
 * - Audit logging
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }
  
  try {
    const { email, password, name } = req.body
    
    // Basic client-side validation (for UX, not security)
    if (!email || !password) {
      return res.status(400).json({
        error: 'Email and password are required'
      })
    }
    
    // Call backend signup endpoint
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${backendUrl}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward IP for rate limiting
        'X-Forwarded-For': (req.headers['x-forwarded-for'] as string) || 
                          (req.headers['x-real-ip'] as string) || 
                          req.socket.remoteAddress || '',
        'User-Agent': req.headers['user-agent'] || ''
      },
      body: JSON.stringify({
        email: email.toLowerCase().trim(),
        password,
        name: name?.trim() || null
      })
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      // Pass through backend error messages
      return res.status(response.status).json({
        error: data.detail || data.error || 'Signup failed',
        errors: data.errors
      })
    }
    
    // Return success response
    return res.status(201).json({
      success: true,
      message: data.message || 'Account created successfully. Please check your email to verify your account.',
      requiresVerification: true,
      user: data.user
    })
    
  } catch (error) {
    console.error('Signup proxy error:', error)
    
    // Network or unexpected errors
    return res.status(500).json({
      error: 'Unable to connect to authentication service. Please try again.'
    })
  }
}