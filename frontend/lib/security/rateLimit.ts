import { prisma } from '@/lib/prisma'

interface RateLimitOptions {
  maxAttempts?: number
  windowMs?: number
}

/**
 * Check if a login attempt is allowed based on rate limiting
 * Default: 5 attempts per minute
 */
export async function checkLoginRateLimit(
  key: string,
  options: RateLimitOptions = {}
): Promise<boolean> {
  const { maxAttempts = 5, windowMs = 60 * 1000 } = options
  
  const windowStart = new Date(Date.now() - windowMs)
  
  // Parse key to get email and IP
  const [, email, ip] = key.split(':')
  
  // Count recent attempts from this email OR IP
  const recentAttempts = await prisma.loginAttempt.count({
    where: {
      OR: [
        { email, createdAt: { gte: windowStart } },
        { ip, createdAt: { gte: windowStart } }
      ]
    }
  })
  
  return recentAttempts < maxAttempts
}

interface LoginAttemptData {
  email: string
  ip: string
  userAgent: string
  success: boolean
  reason: string | null
}

/**
 * Log a login attempt for rate limiting and security monitoring
 */
export async function logLoginAttempt(data: LoginAttemptData): Promise<void> {
  try {
    await prisma.loginAttempt.create({
      data: {
        email: data.email.toLowerCase(),
        ip: data.ip,
        userAgent: data.userAgent?.substring(0, 500), // Limit length
        success: data.success,
        reason: data.reason
      }
    })
    
    // Clean up old login attempts (older than 7 days)
    const cleanupDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    await prisma.loginAttempt.deleteMany({
      where: {
        createdAt: { lt: cleanupDate }
      }
    })
  } catch (error) {
    // Log but don't throw - we don't want rate limiting failures to block login
    console.error('Failed to log login attempt:', error)
  }
}

/**
 * Generic rate limiter for API endpoints
 */
export async function checkApiRateLimit(
  identifier: string,
  endpoint: string,
  options: RateLimitOptions = {}
): Promise<{ allowed: boolean; retryAfter?: number }> {
  const { maxAttempts = 10, windowMs = 60 * 1000 } = options
  
  const key = `api:${endpoint}:${identifier}`
  const windowStart = new Date(Date.now() - windowMs)
  
  // For API rate limiting, we'll use audit logs
  const recentRequests = await prisma.auditLog.count({
    where: {
      event: 'api_request',
      metadata: {
        path: ['endpoint'],
        equals: endpoint
      },
      ip: identifier,
      createdAt: { gte: windowStart }
    }
  })
  
  if (recentRequests >= maxAttempts) {
    const oldestRequest = await prisma.auditLog.findFirst({
      where: {
        event: 'api_request',
        metadata: {
          path: ['endpoint'],
          equals: endpoint
        },
        ip: identifier,
        createdAt: { gte: windowStart }
      },
      orderBy: { createdAt: 'asc' }
    })
    
    if (oldestRequest) {
      const retryAfter = Math.ceil(
        (oldestRequest.createdAt.getTime() + windowMs - Date.now()) / 1000
      )
      return { allowed: false, retryAfter: Math.max(1, retryAfter) }
    }
  }
  
  return { allowed: true }
}

/**
 * Check if an IP is blocked due to suspicious activity
 */
export async function isIpBlocked(ip: string): Promise<boolean> {
  // Check for excessive failed attempts in the last hour
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000)
  
  const failedAttempts = await prisma.loginAttempt.count({
    where: {
      ip,
      success: false,
      createdAt: { gte: oneHourAgo }
    }
  })
  
  // Block if more than 20 failed attempts in an hour
  return failedAttempts > 20
}

/**
 * Clean up expired rate limit records
 */
export async function cleanupRateLimitRecords(): Promise<void> {
  const oneWeekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
  
  await prisma.loginAttempt.deleteMany({
    where: {
      createdAt: { lt: oneWeekAgo }
    }
  })
}