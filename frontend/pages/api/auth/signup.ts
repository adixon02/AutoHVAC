import { NextApiRequest, NextApiResponse } from 'next'
import { prisma } from '@/lib/prisma'
import { hashPassword, validatePasswordStrength } from '@/lib/security/password'
import { checkApiRateLimit, isIpBlocked } from '@/lib/security/rateLimit'
import { createAuditLog } from '@/lib/security/audit'
import { sendVerificationEmail } from '@/lib/email'
import crypto from 'crypto'
import { setCookie } from 'nookies'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }
  
  try {
    const { email, password, name } = req.body
    
    // Validate inputs
    if (!email || !password) {
      return res.status(400).json({
        error: 'Email and password are required'
      })
    }
    
    // Normalize email
    const normalizedEmail = email.toLowerCase().trim()
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(normalizedEmail)) {
      return res.status(400).json({
        error: 'Invalid email format'
      })
    }
    
    // Get IP and user agent
    const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
               req.headers['x-real-ip'] as string || 
               'unknown'
    const userAgent = req.headers['user-agent'] || ''
    
    // Check if IP is blocked
    if (await isIpBlocked(ip)) {
      await createAuditLog({
        event: 'signup_blocked',
        metadata: { email: normalizedEmail, reason: 'ip_blocked' },
        ip,
        userAgent
      })
      return res.status(429).json({
        error: 'Too many attempts. Please try again later.'
      })
    }
    
    // Rate limiting
    const rateLimit = await checkApiRateLimit(ip, 'signup', {
      maxAttempts: 3,
      windowMs: 5 * 60 * 1000 // 3 signups per 5 minutes per IP
    })
    
    if (!rateLimit.allowed) {
      return res.status(429).json({
        error: 'Too many signup attempts. Please try again later.',
        retryAfter: rateLimit.retryAfter
      })
    }
    
    // Validate password strength
    const passwordValidation = validatePasswordStrength(password)
    if (!passwordValidation.isValid) {
      return res.status(400).json({
        error: passwordValidation.errors[0],
        errors: passwordValidation.errors
      })
    }
    
    // Check if user already exists
    const existingUser = await prisma.user.findUnique({
      where: { email: normalizedEmail }
    })
    
    if (existingUser) {
      // Don't reveal that email exists (security)
      // But log it for monitoring
      await createAuditLog({
        event: 'signup_duplicate',
        metadata: { email: normalizedEmail },
        ip,
        userAgent
      })
      
      // Generic message
      return res.status(400).json({
        error: 'Unable to create account. Please try a different email or sign in.'
      })
    }
    
    // Hash password
    const hashedPassword = await hashPassword(password)
    
    // Generate email verification token
    const verificationToken = crypto.randomBytes(32).toString('hex')
    const verificationExpires = new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours
    
    // Create user in transaction
    const user = await prisma.$transaction(async (tx) => {
      // Create user
      const newUser = await tx.user.create({
        data: {
          email: normalizedEmail,
          password: hashedPassword,
          name: name?.trim() || null,
          signupMethod: 'password',
          emailVerified: null // Not verified yet
        }
      })
      
      // Create verification token
      await tx.verificationToken.create({
        data: {
          identifier: normalizedEmail,
          token: verificationToken,
          expires: verificationExpires
        }
      })
      
      // Check for anonymous projects to claim
      const anonId = req.cookies.anon_id
      if (anonId) {
        const claimed = await tx.project.updateMany({
          where: {
            anonId,
            userId: null
          },
          data: {
            userId: newUser.id,
            claimedAt: new Date()
          }
        })
        
        if (claimed.count > 0) {
          await createAuditLog({
            userId: newUser.id,
            event: 'projects_claimed_on_signup',
            metadata: { count: claimed.count, anonId },
            ip,
            userAgent
          })
        }
      }
      
      return newUser
    })
    
    // Create Stripe customer (async, don't block signup)
    if (process.env.STRIPE_SECRET_KEY) {
      // This would be done in a background job ideally
      createStripeCustomer(user.id, normalizedEmail, name).catch(err => {
        console.error('Failed to create Stripe customer:', err)
      })
    }
    
    // Send verification email
    try {
      await sendVerificationEmail({
        to: normalizedEmail,
        token: verificationToken
      })
    } catch (emailError) {
      console.error('Failed to send verification email:', emailError)
      // Don't fail signup if email fails - user can request resend
    }
    
    // Create audit log
    await createAuditLog({
      userId: user.id,
      event: 'account_created',
      metadata: {
        signupMethod: 'password',
        emailSent: true
      },
      ip,
      userAgent
    })
    
    // Clear anonymous ID cookie since projects were claimed
    if (req.cookies.anon_id) {
      setCookie({ res }, 'anon_id', '', {
        maxAge: -1,
        path: '/',
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax'
      })
    }
    
    return res.status(201).json({
      success: true,
      message: 'Account created successfully. Please check your email to verify your account.',
      requiresVerification: true
    })
    
  } catch (error) {
    console.error('Signup error:', error)
    
    // Log error for monitoring
    await createAuditLog({
      event: 'signup_error',
      metadata: {
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      ip: req.headers['x-forwarded-for'] as string || 'unknown',
      userAgent: req.headers['user-agent'] || ''
    })
    
    return res.status(500).json({
      error: 'An error occurred during signup. Please try again.'
    })
  }
}

// Helper function to create Stripe customer (would be in a separate file)
async function createStripeCustomer(
  userId: string,
  email: string,
  name?: string | null
) {
  // This would integrate with Stripe SDK
  // For now, it's a placeholder
  console.log('Would create Stripe customer for:', { userId, email, name })
}