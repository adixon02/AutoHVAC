import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth'
import { authOptions } from './[...nextauth]'
import { prisma } from '@/lib/prisma'
import bcrypt from 'bcryptjs'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { email, password } = req.body

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' })
    }

    // Validate password strength
    if (password.length < 8) {
      return res.status(400).json({ error: 'Password must be at least 8 characters' })
    }

    // Get current session (optional - user might not be signed in yet)
    const session = await getServerSession(req, res, authOptions)

    // Find the user
    const user = await prisma.user.findUnique({
      where: { email: email.toLowerCase() }
    })

    if (!user) {
      return res.status(404).json({ error: 'User not found' })
    }

    // Check if user already has a password
    if (user.password) {
      return res.status(400).json({ error: 'Account already has a password' })
    }

    // Hash the password
    const hashedPassword = await bcrypt.hash(password, 10)

    // Update user with password
    await prisma.user.update({
      where: { id: user.id },
      data: {
        password: hashedPassword,
        emailVerified: new Date(), // Mark as verified since they completed analysis
        signupMethod: 'password',
      }
    })

    // Log the account upgrade
    await prisma.auditLog.create({
      data: {
        userId: user.id,
        event: 'account_upgraded',
        metadata: { 
          from: 'email_only',
          to: 'password_protected'
        }
      }
    })

    res.json({ 
      success: true,
      message: 'Account upgraded successfully'
    })
  } catch (error) {
    console.error('Upgrade account error:', error)
    res.status(500).json({ error: 'Failed to upgrade account' })
  }
}