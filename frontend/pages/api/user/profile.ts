import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '../auth/[...nextauth]'
import { prisma } from '@/lib/prisma'
import { createAuditLog } from '@/lib/security/audit'
import { withCSRFProtection } from '@/lib/security/csrf'

async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Get session
  const session = await getServerSession(req, res, authOptions)
  
  if (!session?.user?.id) {
    return res.status(401).json({ error: 'Unauthorized' })
  }
  
  // GET - Fetch user profile
  if (req.method === 'GET') {
    try {
      const user = await prisma.user.findUnique({
        where: { id: session.user.id },
        select: {
          id: true,
          email: true,
          name: true,
          emailVerified: true,
          freeReportUsed: true,
          createdAt: true,
          lastLoginAt: true,
          loginCount: true
        }
      })
      
      if (!user) {
        return res.status(404).json({ error: 'User not found' })
      }
      
      return res.status(200).json(user)
      
    } catch (error) {
      console.error('Profile fetch error:', error)
      return res.status(500).json({ error: 'Failed to fetch profile' })
    }
  }
  
  // PUT - Update user profile
  if (req.method === 'PUT') {
    try {
      const { name } = req.body
      
      // Validate name
      if (name !== undefined && typeof name !== 'string') {
        return res.status(400).json({ error: 'Invalid name format' })
      }
      
      // Update user
      const updatedUser = await prisma.user.update({
        where: { id: session.user.id },
        data: {
          name: name?.trim() || null,
          updatedAt: new Date()
        },
        select: {
          id: true,
          email: true,
          name: true
        }
      })
      
      // Log the update
      const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
                 req.headers['x-real-ip'] as string || 
                 'unknown'
      const userAgent = req.headers['user-agent'] || ''
      
      await createAuditLog({
        userId: session.user.id,
        event: 'profile_updated',
        metadata: { fields: ['name'] },
        ip,
        userAgent
      })
      
      return res.status(200).json({
        success: true,
        user: updatedUser
      })
      
    } catch (error) {
      console.error('Profile update error:', error)
      return res.status(500).json({ error: 'Failed to update profile' })
    }
  }
  
  return res.status(405).json({ error: 'Method not allowed' })
}

// Apply CSRF protection for state-changing operations
export default withCSRFProtection(handler)