import { NextApiRequest, NextApiResponse } from 'next'
import { prisma } from '@/lib/prisma'
import { createAuditLog } from '@/lib/security/audit'
import { sendWelcomeEmail, sendVerificationEmail } from '@/lib/email'
import { checkApiRateLimit } from '@/lib/security/rateLimit'
import crypto from 'crypto'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
             req.headers['x-real-ip'] as string || 
             'unknown'
  const userAgent = req.headers['user-agent'] || ''
  
  // Handle POST - Verify email with token
  if (req.method === 'POST') {
    try {
      const { token, email } = req.body
      
      if (!token || !email) {
        return res.status(400).json({
          error: 'Token and email are required'
        })
      }
      
      const normalizedEmail = email.toLowerCase().trim()
      
      // Rate limiting
      const rateLimit = await checkApiRateLimit(ip, 'email-verify', {
        maxAttempts: 10,
        windowMs: 15 * 60 * 1000
      })
      
      if (!rateLimit.allowed) {
        return res.status(429).json({
          error: 'Too many attempts. Please try again later.',
          retryAfter: rateLimit.retryAfter
        })
      }
      
      // Find verification token
      const verificationToken = await prisma.verificationToken.findFirst({
        where: {
          token,
          identifier: normalizedEmail,
          expires: { gt: new Date() }
        }
      })
      
      if (!verificationToken) {
        await createAuditLog({
          event: 'email_verification_failed',
          metadata: { 
            email: normalizedEmail,
            reason: 'invalid_token'
          },
          ip,
          userAgent
        })
        
        return res.status(400).json({
          error: 'Invalid or expired verification token'
        })
      }
      
      // Find user
      const user = await prisma.user.findUnique({
        where: { email: normalizedEmail }
      })
      
      if (!user) {
        return res.status(400).json({
          error: 'User not found'
        })
      }
      
      if (user.emailVerified) {
        // Already verified
        return res.status(200).json({
          success: true,
          message: 'Email already verified',
          alreadyVerified: true
        })
      }
      
      // Verify email in transaction
      await prisma.$transaction(async (tx) => {
        // Update user
        await tx.user.update({
          where: { id: user.id },
          data: {
            emailVerified: new Date()
          }
        })
        
        // Delete used token
        await tx.verificationToken.delete({
          where: {
            identifier_token: {
              identifier: normalizedEmail,
              token
            }
          }
        })
        
        // Delete any other verification tokens for this email
        await tx.verificationToken.deleteMany({
          where: {
            identifier: normalizedEmail
          }
        })
      })
      
      // Send welcome email
      try {
        await sendWelcomeEmail({
          to: normalizedEmail,
          name: user.name
        })
      } catch (emailError) {
        console.error('Failed to send welcome email:', emailError)
        // Don't fail the verification if welcome email fails
      }
      
      // Create audit log
      await createAuditLog({
        userId: user.id,
        event: 'email_verified',
        metadata: { welcomeEmailSent: true },
        ip,
        userAgent
      })
      
      return res.status(200).json({
        success: true,
        message: 'Email verified successfully',
        redirect: '/dashboard'
      })
      
    } catch (error) {
      console.error('Email verification error:', error)
      
      await createAuditLog({
        event: 'email_verification_error',
        metadata: { error: error instanceof Error ? error.message : 'Unknown' },
        ip,
        userAgent
      })
      
      return res.status(500).json({
        error: 'An error occurred during verification'
      })
    }
  }
  
  // Handle GET - Resend verification email
  if (req.method === 'GET') {
    try {
      const { email } = req.query
      
      if (!email || typeof email !== 'string') {
        return res.status(400).json({
          error: 'Email is required'
        })
      }
      
      const normalizedEmail = email.toLowerCase().trim()
      
      // Rate limiting - strict for resend
      const rateLimit = await checkApiRateLimit(ip, 'email-resend', {
        maxAttempts: 3,
        windowMs: 15 * 60 * 1000 // 3 resends per 15 minutes
      })
      
      if (!rateLimit.allowed) {
        return res.status(429).json({
          error: 'Too many resend attempts. Please try again later.',
          retryAfter: rateLimit.retryAfter
        })
      }
      
      // Find user
      const user = await prisma.user.findUnique({
        where: { email: normalizedEmail }
      })
      
      // Always return success to prevent enumeration
      if (user && !user.emailVerified) {
        // Check for recent token
        const recentToken = await prisma.verificationToken.findFirst({
          where: {
            identifier: normalizedEmail,
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
            event: 'email_verification_resend_throttled',
            metadata: { reason: 'recent_token' },
            ip,
            userAgent
          })
        } else {
          // Create new verification token
          const verificationToken = crypto.randomBytes(32).toString('hex')
          const verificationExpires = new Date(Date.now() + 24 * 60 * 60 * 1000)
          
          await prisma.verificationToken.create({
            data: {
              identifier: normalizedEmail,
              token: verificationToken,
              expires: verificationExpires
            }
          })
          
          // Send email
          try {
            await sendVerificationEmail({
              to: normalizedEmail,
              token: verificationToken
            })
            
            await createAuditLog({
              userId: user.id,
              event: 'email_verification_resent',
              metadata: { emailSent: true },
              ip,
              userAgent
            })
          } catch (emailError) {
            console.error('Failed to resend verification email:', emailError)
          }
        }
      }
      
      return res.status(200).json({
        success: true,
        message: 'If your account needs verification, you will receive an email shortly.'
      })
      
    } catch (error) {
      console.error('Resend verification error:', error)
      
      await createAuditLog({
        event: 'email_verification_resend_error',
        metadata: { error: error instanceof Error ? error.message : 'Unknown' },
        ip,
        userAgent
      })
      
      return res.status(500).json({
        error: 'An error occurred. Please try again later.'
      })
    }
  }
  
  return res.status(405).json({
    error: 'Method not allowed'
  })
}