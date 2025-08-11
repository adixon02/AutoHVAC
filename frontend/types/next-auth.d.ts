import NextAuth, { DefaultSession } from "next-auth"

declare module "next-auth" {
  /**
   * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
   */
  interface Session {
    user: {
      id: string
      emailVerified: boolean
      freeReportUsed: boolean
      hasActiveSubscription: boolean
      hasPassword: boolean
      stripeCustomerId?: string | null
    } & DefaultSession["user"]
  }

  interface User {
    id: string
    emailVerified: Date | null
    freeReportUsed: boolean
    stripeCustomerId?: string | null
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string
    hasPassword: boolean
    emailVerified: Date | null
    freeReportUsed: boolean
  }
}