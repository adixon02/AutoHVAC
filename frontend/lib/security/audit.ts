import { prisma } from '@/lib/prisma'

interface AuditLogData {
  userId?: string | null
  event: string
  metadata?: any
  ip?: string | null
  userAgent?: string | null
}

/**
 * Create an audit log entry for security and compliance
 */
export async function createAuditLog(data: AuditLogData): Promise<void> {
  try {
    await prisma.auditLog.create({
      data: {
        userId: data.userId,
        event: data.event,
        metadata: data.metadata || {},
        ip: data.ip,
        userAgent: data.userAgent?.substring(0, 500) // Limit length
      }
    })
    
    // Clean up old audit logs (older than 90 days for compliance)
    const cleanupDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
    await prisma.auditLog.deleteMany({
      where: {
        createdAt: { lt: cleanupDate },
        // Keep certain critical events longer
        event: {
          notIn: [
            'account_created',
            'account_deleted',
            'password_change',
            'subscription_created',
            'subscription_canceled'
          ]
        }
      }
    })
  } catch (error) {
    // Log but don't throw - audit logging should not break the app
    console.error('Failed to create audit log:', error)
  }
}

/**
 * Query audit logs for a specific user
 */
export async function getUserAuditLogs(
  userId: string,
  options: {
    limit?: number
    offset?: number
    event?: string
    startDate?: Date
    endDate?: Date
  } = {}
) {
  const {
    limit = 50,
    offset = 0,
    event,
    startDate,
    endDate
  } = options
  
  const where: any = { userId }
  
  if (event) {
    where.event = event
  }
  
  if (startDate || endDate) {
    where.createdAt = {}
    if (startDate) where.createdAt.gte = startDate
    if (endDate) where.createdAt.lte = endDate
  }
  
  const [logs, total] = await Promise.all([
    prisma.auditLog.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      take: limit,
      skip: offset
    }),
    prisma.auditLog.count({ where })
  ])
  
  return { logs, total }
}

/**
 * Get security events for monitoring
 */
export async function getSecurityEvents(
  options: {
    timeWindow?: number // milliseconds
    eventTypes?: string[]
  } = {}
) {
  const {
    timeWindow = 60 * 60 * 1000, // Default 1 hour
    eventTypes = [
      'login',
      'login_failed',
      'password_change',
      'password_reset',
      'account_locked',
      'suspicious_activity'
    ]
  } = options
  
  const since = new Date(Date.now() - timeWindow)
  
  const events = await prisma.auditLog.findMany({
    where: {
      event: { in: eventTypes },
      createdAt: { gte: since }
    },
    orderBy: { createdAt: 'desc' },
    take: 100
  })
  
  // Group by event type for summary
  const summary = events.reduce((acc, event) => {
    acc[event.event] = (acc[event.event] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  return { events, summary }
}

/**
 * Log suspicious activity for security monitoring
 */
export async function logSuspiciousActivity(
  details: {
    userId?: string | null
    ip?: string | null
    userAgent?: string | null
    reason: string
    metadata?: any
  }
) {
  await createAuditLog({
    userId: details.userId,
    event: 'suspicious_activity',
    metadata: {
      reason: details.reason,
      ...details.metadata
    },
    ip: details.ip,
    userAgent: details.userAgent
  })
}

/**
 * Check if user has recent suspicious activity
 */
export async function hasRecentSuspiciousActivity(
  userId: string,
  windowMs: number = 24 * 60 * 60 * 1000 // 24 hours
): Promise<boolean> {
  const since = new Date(Date.now() - windowMs)
  
  const count = await prisma.auditLog.count({
    where: {
      userId,
      event: 'suspicious_activity',
      createdAt: { gte: since }
    }
  })
  
  return count > 0
}