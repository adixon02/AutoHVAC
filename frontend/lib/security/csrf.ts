import crypto from 'crypto'
import { NextApiRequest, NextApiResponse } from 'next'
import { getCookie, setCookie } from 'nookies'

const CSRF_TOKEN_COOKIE = 'csrf-token'
const CSRF_HEADER = 'x-csrf-token'

/**
 * Generate a CSRF token
 */
export function generateCSRFToken(): string {
  return crypto.randomBytes(32).toString('hex')
}

/**
 * Get or create CSRF token for a request
 */
export function getOrCreateCSRFToken(
  req: NextApiRequest,
  res: NextApiResponse
): string {
  const cookies = getCookie({ req })
  let token = cookies[CSRF_TOKEN_COOKIE]
  
  if (!token) {
    token = generateCSRFToken()
    setCookie({ res }, CSRF_TOKEN_COOKIE, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      path: '/',
      maxAge: 60 * 60 * 24 // 24 hours
    })
  }
  
  return token
}

/**
 * Verify CSRF token
 */
export function verifyCSRFToken(
  req: NextApiRequest
): boolean {
  // Skip for safe methods
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method || '')) {
    return true
  }
  
  const cookies = getCookie({ req })
  const cookieToken = cookies[CSRF_TOKEN_COOKIE]
  const headerToken = req.headers[CSRF_HEADER] as string
  
  if (!cookieToken || !headerToken) {
    return false
  }
  
  // Constant-time comparison
  return crypto.timingSafeEqual(
    Buffer.from(cookieToken),
    Buffer.from(headerToken)
  )
}

/**
 * CSRF protection middleware
 */
export function withCSRFProtection(
  handler: (req: NextApiRequest, res: NextApiResponse) => Promise<any>
) {
  return async (req: NextApiRequest, res: NextApiResponse) => {
    // Verify CSRF token for state-changing requests
    if (!verifyCSRFToken(req)) {
      return res.status(403).json({ 
        error: 'Invalid CSRF token' 
      })
    }
    
    return handler(req, res)
  }
}

/**
 * Get CSRF token for client-side use
 */
export function getCSRFTokenForClient(req: NextApiRequest): string | null {
  const cookies = getCookie({ req })
  return cookies[CSRF_TOKEN_COOKIE] || null
}