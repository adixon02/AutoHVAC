import NextAuth, { NextAuthOptions } from 'next-auth'
import EmailProvider from 'next-auth/providers/email'
import { createTransport } from 'nodemailer'

// Simple in-memory adapter for MVP (replace with database adapter in production)
const users: Record<string, any> = {}
const verificationTokens: Record<string, any> = {}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  
  providers: [
    EmailProvider({
      server: {
        host: process.env.EMAIL_SERVER_HOST || 'smtp.gmail.com',
        port: Number(process.env.EMAIL_SERVER_PORT) || 587,
        auth: {
          user: process.env.EMAIL_SERVER_USER,
          pass: process.env.EMAIL_SERVER_PASSWORD,
        },
      },
      from: process.env.EMAIL_FROM || 'noreply@autohvac.com',
      async sendVerificationRequest({ identifier: email, url, provider }: any) {
        const transport = createTransport(provider.server)
        const result = await transport.sendMail({
          to: email,
          from: provider.from,
          subject: 'Sign in to AutoHVAC',
          text: `Sign in to AutoHVAC\n\n${url}\n\n`,
          html: `
            <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
              <h1 style="color: #1a56db; text-align: center;">Sign in to AutoHVAC</h1>
              <p style="color: #374151; font-size: 16px;">Click the button below to sign in to your account:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="${url}" style="background-color: #1a56db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                  Sign In
                </a>
              </div>
              <p style="color: #6b7280; font-size: 14px;">Or copy and paste this URL into your browser:</p>
              <p style="color: #6b7280; font-size: 14px; word-break: break-all;">${url}</p>
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
              <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                If you didn't request this email, you can safely ignore it.
              </p>
            </div>
          `,
        })
        
        const failed = result.rejected.filter(Boolean)
        if (failed.length) {
          throw new Error(`Email(s) (${failed.join(', ')}) could not be sent`)
        }
      },
    }),
  ],
  
  adapter: {
    // Simple in-memory adapter for MVP
    async createUser(user: any) {
      const id = crypto.randomUUID()
      users[id] = { ...user, id }
      return users[id]
    },
    async getUser(id: any) {
      return users[id] || null
    },
    async getUserByEmail(email: any) {
      return Object.values(users).find((u: any) => u.email === email) || null
    },
    async getUserByAccount({ providerAccountId }: any) {
      return users[providerAccountId] || null
    },
    async updateUser(user: any) {
      users[user.id] = user
      return user
    },
    async linkAccount(account: any) {
      return account
    },
    async createSession(session: any) {
      return session
    },
    async getSessionAndUser(sessionToken: any) {
      // For magic links, we don't need complex session management
      return null
    },
    async updateSession(session: any) {
      return session
    },
    async deleteSession(sessionToken: any) {
      // No-op for in-memory
    },
    async createVerificationToken(verificationToken: any) {
      verificationTokens[verificationToken.identifier] = verificationToken
      return verificationToken
    },
    async useVerificationToken({ identifier, token }: any) {
      const stored = verificationTokens[identifier]
      if (stored && stored.token === token && stored.expires > new Date()) {
        delete verificationTokens[identifier]
        return stored
      }
      return null
    },
  },
  
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  
  jwt: {
    secret: process.env.NEXTAUTH_SECRET,
  },
  
  cookies: {
    sessionToken: {
      name: `${process.env.NODE_ENV === 'production' ? '__Secure-' : ''}next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
    callbackUrl: {
      name: `${process.env.NODE_ENV === 'production' ? '__Secure-' : ''}next-auth.callback-url`,
      options: {
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
    csrfToken: {
      name: `${process.env.NODE_ENV === 'production' ? '__Host-' : ''}next-auth.csrf-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
  
  pages: {
    signIn: '/auth/signin',
    verifyRequest: '/auth/verify',
    error: '/auth/error',
  },
  
  callbacks: {
    async session({ session, token }: any) {
      if (session?.user?.email) {
        // Add user email to session
        session.user.email = token.email as string
      }
      return session
    },
    async jwt({ token, user }: any) {
      if (user) {
        token.email = user.email
      }
      return token
    },
  },
  
  debug: process.env.NODE_ENV === 'development',
}

export default NextAuth(authOptions)