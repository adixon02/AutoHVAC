import NextAuth, { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import { PrismaAdapter } from '@next-auth/prisma-adapter'
import { prisma } from '@/lib/prisma'
import bcrypt from 'bcryptjs'

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  
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
        
        const email = credentials.email.toLowerCase()
        
        // Get or create user (no password required)
        let user = await prisma.user.findUnique({
          where: { email }
        })
        
        if (!user) {
          // Create new user with just email
          user = await prisma.user.create({
            data: { 
              email,
              emailVerified: null, // Not verified yet
              signupMethod: 'email_only'
            }
          })
        }
        
        return {
          id: user.id,
          email: user.email,
          name: user.name,
          image: user.image,
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
        
        const email = credentials.email.toLowerCase()
        
        const user = await prisma.user.findUnique({
          where: { email }
        })
        
        // Check if user exists and has a password
        if (user && user.password) {
          const valid = await bcrypt.compare(credentials.password, user.password)
          if (valid) {
            // Update login metadata
            await prisma.user.update({
              where: { id: user.id },
              data: {
                lastLoginAt: new Date(),
                loginCount: { increment: 1 },
                failedLoginAttempts: 0, // Reset on successful login
              }
            })
            
            return {
              id: user.id,
              email: user.email,
              name: user.name,
              image: user.image,
            }
          } else {
            // Increment failed attempts
            await prisma.user.update({
              where: { id: user.id },
              data: {
                failedLoginAttempts: { increment: 1 }
              }
            })
          }
        }
        
        return null
      }
    })
  ],
  
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.id = user.id
        token.email = user.email
        
        // Check if user has a password
        const dbUser = await prisma.user.findUnique({
          where: { id: user.id },
          select: { password: true, emailVerified: true, freeReportUsed: true }
        })
        
        token.hasPassword = !!dbUser?.password
        token.emailVerified = dbUser?.emailVerified
        token.freeReportUsed = dbUser?.freeReportUsed || false
      }
      return token
    },
    
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
        session.user.hasPassword = token.hasPassword as boolean
        session.user.emailVerified = token.emailVerified as Date | null
        session.user.freeReportUsed = token.freeReportUsed as boolean
      }
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