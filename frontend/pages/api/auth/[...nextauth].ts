import NextAuth, { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const authOptions: NextAuthOptions = {
  // Remove Prisma adapter - we're using the backend as source of truth
  
  session: { 
    strategy: 'jwt',  // Use JWT for stateless sessions
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  
  providers: [
    // Email-only provider (no password required)
    CredentialsProvider({
      id: 'email-only',
      name: 'Email Only',
      credentials: {
        email: { label: "Email", type: "email" }
      },
      async authorize(credentials) {
        if (!credentials?.email) return null
        
        try {
          // Call backend login endpoint
          const response = await fetch(`${BACKEND_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: credentials.email.toLowerCase(),
              password: null  // Email-only login
            })
          })
          
          if (!response.ok) {
            return null
          }
          
          const data = await response.json()
          
          // Return user data with backend JWT token
          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            image: data.user.image,
            emailVerified: data.user.emailVerified,
            freeReportUsed: data.user.freeReportUsed,
            stripeCustomerId: data.user.stripeCustomerId,
            accessToken: data.access_token  // Store backend JWT
          }
        } catch (error) {
          console.error('Login error:', error)
          return null
        }
      }
    }),
    
    // Standard credentials provider (email + password)
    CredentialsProvider({
      id: 'credentials',
      name: 'Email and Password',
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null
        
        try {
          // Call backend login endpoint with password
          const response = await fetch(`${BACKEND_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: credentials.email.toLowerCase(),
              password: credentials.password
            })
          })
          
          if (!response.ok) {
            return null
          }
          
          const data = await response.json()
          
          // Return user data with backend JWT token
          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            image: data.user.image,
            emailVerified: data.user.emailVerified,
            freeReportUsed: data.user.freeReportUsed,
            stripeCustomerId: data.user.stripeCustomerId,
            accessToken: data.access_token  // Store backend JWT
          }
        } catch (error) {
          console.error('Login error:', error)
          return null
        }
      }
    })
  ],
  
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.id = user.id
        token.email = user.email
        token.emailVerified = user.emailVerified
        token.freeReportUsed = user.freeReportUsed
        token.stripeCustomerId = user.stripeCustomerId
        token.accessToken = (user as any).accessToken  // Store backend JWT
      }
      return token
    },
    
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
        session.user.emailVerified = !!token.emailVerified
        session.user.freeReportUsed = token.freeReportUsed as boolean
        session.user.stripeCustomerId = token.stripeCustomerId as string | null
        session.user.hasActiveSubscription = false // Will be fetched from backend
        session.user.hasPassword = true // Backend handles this
      }
      // Include backend JWT for API calls
      (session as any).accessToken = token.accessToken
      return session
    }
  },
  
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  
  events: {
    async signIn({ user }) {
      // Log sign in event
      await prisma.auditLog.create({
        data: {
          userId: user.id,
          event: 'login',
          metadata: { method: 'credentials' },
        }
      })
    },
    
    async signOut({ token }) {
      if (token?.id) {
        // Log sign out event
        await prisma.auditLog.create({
          data: {
            userId: token.id as string,
            event: 'logout',
            metadata: {},
          }
        })
      }
    }
  },
  
  debug: process.env.NODE_ENV === 'development',
}

export default NextAuth(authOptions)