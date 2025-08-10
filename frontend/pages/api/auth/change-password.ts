import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from './[...nextauth]'
import { changePassword } from '@/lib/security/password'
import { withCSRFProtection } from '@/lib/security/csrf'

async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }
  
  try {
    // Get session
    const session = await getServerSession(req, res, authOptions)
    
    if (!session?.user?.id) {
      return res.status(401).json({ error: 'Unauthorized' })
    }
    
    const { currentPassword, newPassword } = req.body
    
    if (!currentPassword || !newPassword) {
      return res.status(400).json({ error: 'Current and new passwords are required' })
    }
    
    // Get IP and user agent for audit log
    const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
               req.headers['x-real-ip'] as string || 
               'unknown'
    const userAgent = req.headers['user-agent'] || ''
    
    // Change password
    const result = await changePassword(
      session.user.id,
      currentPassword,
      newPassword,
      ip,
      userAgent
    )
    
    if (!result.success) {
      return res.status(400).json({ error: result.error })
    }
    
    return res.status(200).json({ 
      success: true,
      message: 'Password changed successfully'
    })
    
  } catch (error) {
    console.error('Password change error:', error)
    return res.status(500).json({ 
      error: 'Failed to change password' 
    })
  }
}

// Apply CSRF protection
export default withCSRFProtection(handler)