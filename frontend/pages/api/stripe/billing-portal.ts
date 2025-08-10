import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '../auth/[...nextauth]'
import { createBillingPortalSession } from '@/lib/stripe'
import { createAuditLog } from '@/lib/security/audit'

export default async function handler(
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
    
    const { returnUrl } = req.body
    
    // Use default return URL if not provided
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000'
    const finalReturnUrl = returnUrl || `${baseUrl}/dashboard`
    
    // Create billing portal session
    const portalUrl = await createBillingPortalSession({
      userId: session.user.id,
      returnUrl: finalReturnUrl
    })
    
    // Log the action
    const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
               req.headers['x-real-ip'] as string || 
               'unknown'
    const userAgent = req.headers['user-agent'] || ''
    
    await createAuditLog({
      userId: session.user.id,
      event: 'billing_portal_requested',
      metadata: {},
      ip,
      userAgent
    })
    
    return res.status(200).json({ 
      success: true,
      portalUrl 
    })
    
  } catch (error) {
    console.error('Billing portal error:', error)
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    
    // Special handling for no customer error
    if (errorMessage.includes('No Stripe customer')) {
      return res.status(400).json({ 
        error: 'No billing information found. Please subscribe first.' 
      })
    }
    
    return res.status(500).json({ 
      error: 'Failed to access billing portal' 
    })
  }
}