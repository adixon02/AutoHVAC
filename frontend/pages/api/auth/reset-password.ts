import { NextApiRequest, NextApiResponse } from 'next'
import { prisma } from '@/lib/prisma'
import { 
  createPasswordResetToken, 
  resetPasswordWithToken 
} from '@/lib/security/password'
import { checkApiRateLimit, isIpBlocked } from '@/lib/security/rateLimit'
import { createAuditLog } from '@/lib/security/audit'
import { sendPasswordResetEmail } from '@/lib/email'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
             req.headers['x-real-ip'] as string || 
             'unknown'
  const userAgent = req.headers['user-agent'] || ''
  
  // Check if IP is blocked
  if (await isIpBlocked(ip)) {
    return res.status(429).json({
      error: 'Too many attempts. Please try again later.'
    })
  }
  
  // Handle POST - Request password reset
  if (req.method === 'POST') {
    try {
      const { email } = req.body
      
      if (!email) {
        return res.status(400).json({
          error: 'Email is required'
        })
      }
      
      const normalizedEmail = email.toLowerCase().trim()
      
      // Rate limiting - strict for password reset
      const rateLimit = await checkApiRateLimit(ip, 'password-reset-request', {
        maxAttempts: 3,
        windowMs: 15 * 60 * 1000 // 3 requests per 15 minutes
      })
      
      if (!rateLimit.allowed) {
        await createAuditLog({
          event: 'password_reset_rate_limited',
          metadata: { email: normalizedEmail },
          ip,
          userAgent
        })
        
        return res.status(429).json({
          error: 'Too many password reset attempts. Please try again later.',
          retryAfter: rateLimit.retryAfter
        })
      }
      
      // Check if user exists
      const user = await prisma.user.findUnique({
        where: { email: normalizedEmail }
      })
      
      // Always return success to prevent email enumeration
      // But only send email if user exists
      if (user) {
        // Check for recent reset requests (prevent spam)
        const recentToken = await prisma.passwordResetToken.findFirst({
          where: {
            email: normalizedEmail,
            used: false,
            expires: { gt: new Date() },
            createdAt: { 
              gt: new Date(Date.now() - 5 * 60 * 1000) // Within last 5 minutes
            }
          }
        })
        
        if (recentToken) {
          // Don't create new token if one was recently sent
          await createAuditLog({
            userId: user.id,
            event: 'password_reset_throttled',
            metadata: { reason: 'recent_request' },
            ip,
            userAgent
          })
        } else {
          // Create reset token
          const { token, expires } = await createPasswordResetToken(normalizedEmail)
          
          // Send email
          try {
            await sendPasswordResetEmail({
              to: normalizedEmail,
              token
            })
            
            await createAuditLog({
              userId: user.id,
              event: 'password_reset_requested',
              metadata: { emailSent: true },
              ip,
              userAgent
            })
          } catch (emailError) {
            console.error('Failed to send password reset email:', emailError)
            
            await createAuditLog({
              userId: user.id,
              event: 'password_reset_email_failed',
              metadata: { error: emailError },
              ip,
              userAgent
            })
            
            // Still return success to prevent enumeration
          }
        }
      } else {
        // Log attempt for non-existent user (for security monitoring)
        await createAuditLog({
          event: 'password_reset_nonexistent',
          metadata: { email: normalizedEmail },
          ip,
          userAgent
        })
      }
      
      // Always return same response
      return res.status(200).json({
        success: true,
        message: 'If an account exists with this email, you will receive password reset instructions.'
      })
      
    } catch (error) {
      console.error('Password reset request error:', error)
      
      await createAuditLog({
        event: 'password_reset_error',
        metadata: { error: error instanceof Error ? error.message : 'Unknown' },
        ip,
        userAgent
      })
      
      return res.status(500).json({
        error: 'An error occurred. Please try again later.'
      })
    }
  }
  
  // Handle PUT - Reset password with token
  if (req.method === 'PUT') {
    try {
      const { token, email, password } = req.body
      
      if (!token || !email || !password) {
        return res.status(400).json({
          error: 'Token, email, and new password are required'
        })
      }
      
      const normalizedEmail = email.toLowerCase().trim()
      
      // Rate limiting for password reset attempts
      const rateLimit = await checkApiRateLimit(ip, 'password-reset-complete', {
        maxAttempts: 5,
        windowMs: 15 * 60 * 1000 // 5 attempts per 15 minutes
      })
      
      if (!rateLimit.allowed) {
        return res.status(429).json({
          error: 'Too many attempts. Please try again later.',
          retryAfter: rateLimit.retryAfter
        })
      }
      
      // Reset password
      const result = await resetPasswordWithToken(
        token,
        normalizedEmail,
        password,
        ip,
        userAgent
      )
      
      if (!result.success) {
        // Log failed attempt
        await createAuditLog({
          event: 'password_reset_failed',
          metadata: { 
            email: normalizedEmail,
            reason: result.error 
          },
          ip,
          userAgent
        })
        
        return res.status(400).json({
          error: result.error || 'Failed to reset password'
        })
      }
      
      return res.status(200).json({
        success: true,
        message: 'Password has been reset successfully. You can now sign in with your new password.'
      })
      
    } catch (error) {
      console.error('Password reset error:', error)
      
      await createAuditLog({
        event: 'password_reset_error',
        metadata: { error: error instanceof Error ? error.message : 'Unknown' },
        ip,
        userAgent
      })
      
      return res.status(500).json({
        error: 'An error occurred. Please try again later.'
      })
    }
  }
  
  // Method not allowed
  return res.status(405).json({
    error: 'Method not allowed'
  })
}