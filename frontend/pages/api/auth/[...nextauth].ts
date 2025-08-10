import NextAuth, { NextAuthOptions } from 'next-auth'
import EmailProvider from 'next-auth/providers/email'
import CredentialsProvider from 'next-auth/providers/credentials'
import GoogleProvider from 'next-auth/providers/google'
import { PrismaAdapter } from '@next-auth/prisma-adapter'
import { prisma } from '@/lib/prisma'
import bcrypt from 'bcryptjs'
import { parseCookies } from 'nookies'
import { checkLoginRateLimit, logLoginAttempt } from '@/lib/security/rateLimit'
import { createAuditLog } from '@/lib/security/audit'

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  
  // Use DATABASE sessions for maximum security (not JWT)
  session: {
    strategy: 'database',
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60,    // Update session every 24 hours
  },
  
  providers: [
    // Magic Links - Passwordless authentication
    EmailProvider({
      server: process.env.EMAIL_SERVER || {
        host: process.env.EMAIL_SERVER_HOST || 'smtp.gmail.com',
        port: Number(process.env.EMAIL_SERVER_PORT) || 587,
        auth: {
          user: process.env.EMAIL_SERVER_USER,
          pass: process.env.EMAIL_SERVER_PASSWORD,
        },
      },
      from: process.env.EMAIL_FROM || 'AutoHVAC <noreply@autohvac.ai>',
      maxAge: 24 * 60 * 60, // Magic links valid for 24 hours
    }),
    
    // Password Authentication with security checks
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: "Email", type: "email", placeholder: "you@example.com" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials, req) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }
        
        const email = credentials.email.toLowerCase()
        const ip = (req.headers?.['x-forwarded-for'] as string)?.split(',')[0] || 
                   req.headers?.['x-real-ip'] || 
                   'unknown'
        const userAgent = req.headers?.['user-agent'] || ''
        
        // Rate limiting check
        const rateLimitKey = `login:${email}:${ip}`
        const isAllowed = await checkLoginRateLimit(rateLimitKey)
        
        if (!isAllowed) {
          await logLoginAttempt({
            email,
            ip,
            userAgent,
            success: false,
            reason: 'rate_limited'
          })
          // Generic error to prevent enumeration
          throw new Error('Invalid credentials')
        }
        
        // Find user
        const user = await prisma.user.findUnique({
          where: { email }
        })
        
        // Check if account is locked
        if (user?.lockedUntil && user.lockedUntil > new Date()) {
          await logLoginAttempt({
            email,
            ip,
            userAgent,
            success: false,
            reason: 'account_locked'
          })
          throw new Error('Invalid credentials') // Generic error
        }
        
        // Check if user exists and has password
        if (!user?.password) {
          await logLoginAttempt({
            email,
            ip,
            userAgent,
            success: false,
            reason: 'invalid_credentials'
          })
          throw new Error('Invalid credentials')
        }
        
        // Verify password
        const isValid = await bcrypt.compare(credentials.password, user.password)
        
        if (!isValid) {
          // Increment failed attempts
          const attempts = user.failedLoginAttempts + 1
          const updateData: any = { failedLoginAttempts: attempts }
          
          // Lock account after 5 failed attempts for 15 minutes
          if (attempts >= 5) {
            updateData.lockedUntil = new Date(Date.now() + 15 * 60 * 1000)
          }
          
          await prisma.user.update({
            where: { id: user.id },
            data: updateData
          })
          
          await logLoginAttempt({
            email,
            ip,
            userAgent,
            success: false,
            reason: 'invalid_password'
          })
          
          throw new Error('Invalid credentials')
        }
        
        // Check email verification for security
        if (!user.emailVerified) {
          await logLoginAttempt({
            email,
            ip,
            userAgent,
            success: false,
            reason: 'email_not_verified'
          })
          throw new Error('Please verify your email first')
        }
        
        // Successful login - reset failed attempts and update metadata
        await prisma.user.update({
          where: { id: user.id },
          data: {
            lastLoginAt: new Date(),
            loginCount: { increment: 1 },
            failedLoginAttempts: 0,
            lockedUntil: null
          }
        })
        
        await logLoginAttempt({
          email,
          ip,
          userAgent,
          success: true,
          reason: null
        })
        
        await createAuditLog({
          userId: user.id,
          event: 'login',
          metadata: { method: 'password' },
          ip,
          userAgent
        })
        
        return {
          id: user.id,
          email: user.email,
          name: user.name,
          image: user.image,
          emailVerified: user.emailVerified,
          freeReportUsed: user.freeReportUsed,
          stripeCustomerId: user.stripeCustomerId,
        }
      }
    }),
    
    // Google OAuth (if configured)
    ...(process.env.GOOGLE_CLIENT_ID ? [
      GoogleProvider({
        clientId: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
        authorization: {
          params: {
            prompt: "consent",
            access_type: "offline",
            response_type: "code"
          }
        }
      })
    ] : [])
  ],
  
  callbacks: {
    async session({ session, user }) {
      // Add user ID to session
      session.user.id = user.id
      session.user.emailVerified = !!user.emailVerified
      
      // Get current subscription status (server-side truth)
      const subscription = await prisma.subscription.findFirst({
        where: {
          userId: user.id,
          status: { in: ['active', 'trialing'] },
          currentPeriodEnd: { gt: new Date() }
        }
      })
      
      // Add business logic flags (for UI only, always verify server-side)
      session.user.freeReportUsed = user.freeReportUsed
      session.user.hasActiveSubscription = !!subscription
      session.user.stripeCustomerId = user.stripeCustomerId
      
      return session
    },
    
    async signIn({ user, account, profile, email, credentials }) {
      // Log OAuth sign in
      if (account?.provider && account.provider !== 'credentials') {
        await createAuditLog({
          userId: user.id,
          event: 'login',
          metadata: { method: account.provider },
          ip: null,
          userAgent: null
        })
      }
      
      // Claim anonymous projects on sign in
      const ctx = (credentials as any)?.req || (account as any)?.req
      if (ctx) {
        const cookies = parseCookies({ req: ctx })
        const anonId = cookies.anon_id
        
        if (anonId) {
          // Atomically claim all anonymous projects
          const claimed = await prisma.project.updateMany({
            where: {
              anonId: anonId,
              userId: null
            },
            data: {
              userId: user.id,
              claimedAt: new Date()
            }
          })
          
          if (claimed.count > 0) {
            await createAuditLog({
              userId: user.id,
              event: 'projects_claimed',
              metadata: { count: claimed.count, anonId },
              ip: null,
              userAgent: null
            })
          }
        }
      }
      
      return true
    },
    
    async redirect({ url, baseUrl }) {
      // Ensure we only redirect to our domain
      if (url.startsWith('/')) return `${baseUrl}${url}`
      else if (new URL(url).origin === baseUrl) return url
      return baseUrl
    }
  },
  
  events: {
    async signOut({ session, token }) {
      if (session?.user?.id) {
        await createAuditLog({
          userId: session.user.id,
          event: 'logout',
          metadata: {},
          ip: null,
          userAgent: null
        })
      }
    },
    
    async createUser({ user }) {
      await createAuditLog({
        userId: user.id,
        event: 'account_created',
        metadata: { signupMethod: 'magic_link' },
        ip: null,
        userAgent: null
      })
    }
  },
  
  cookies: {
    sessionToken: {
      name: process.env.NODE_ENV === 'production' 
        ? '__Secure-next-auth.session-token'
        : 'next-auth.session-token',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
        domain: process.env.NODE_ENV === 'production' ? '.autohvac.ai' : undefined
      }
    },
    callbackUrl: {
      name: process.env.NODE_ENV === 'production'
        ? '__Secure-next-auth.callback-url'
        : 'next-auth.callback-url',
      options: {
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
        domain: process.env.NODE_ENV === 'production' ? '.autohvac.ai' : undefined
      }
    },
    csrfToken: {
      name: process.env.NODE_ENV === 'production'
        ? '__Host-next-auth.csrf-token'
        : 'next-auth.csrf-token',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production'
      }
    }
  },
  
  pages: {
    signIn: '/auth/signin',
    signUp: '/auth/signup',
    error: '/auth/error',
    verifyRequest: '/auth/verify',
    newUser: '/welcome'
  },
  
  debug: process.env.NODE_ENV === 'development',
}

export default NextAuth(authOptions)