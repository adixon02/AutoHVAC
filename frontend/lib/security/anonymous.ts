import { NextApiRequest, NextApiResponse } from 'next'
import { parseCookies, setCookie } from 'nookies'
import crypto from 'crypto'

const ANON_ID_COOKIE = 'anon_id'

/**
 * Generate a secure anonymous ID
 */
export function generateAnonymousId(): string {
  return crypto.randomBytes(16).toString('hex')
}

/**
 * Get or create anonymous ID for tracking
 */
export function getOrCreateAnonymousId(
  req: NextApiRequest,
  res: NextApiResponse
): string {
  const cookies = parseCookies({ req })
  let anonId = cookies[ANON_ID_COOKIE]
  
  if (!anonId) {
    anonId = generateAnonymousId()
    setAnonymousId(res, anonId)
  }
  
  return anonId
}

/**
 * Set anonymous ID cookie
 */
export function setAnonymousId(
  res: NextApiResponse,
  anonId: string
): void {
  setCookie({ res }, ANON_ID_COOKIE, anonId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 30 * 24 * 60 * 60 // 30 days
  })
}

/**
 * Clear anonymous ID (after user signs up/in)
 */
export function clearAnonymousId(res: NextApiResponse): void {
  setCookie({ res }, ANON_ID_COOKIE, '', {
    maxAge: -1,
    path: '/'
  })
}

/**
 * Get anonymous ID from request
 */
export function getAnonymousId(req: NextApiRequest): string | null {
  const cookies = parseCookies({ req })
  return cookies[ANON_ID_COOKIE] || null
}