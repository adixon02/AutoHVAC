import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '../auth/[...nextauth]'
import { createCheckoutSession } from '@/lib/stripe'
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
    
    // Check if email is verified
    if (!session.user.emailVerified) {
      return res.status(403).json({ 
        error: 'Please verify your email before subscribing' 
      })
    }
    
    const { priceId, successUrl, cancelUrl } = req.body
    
    // Use default URLs if not provided
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000'
    const finalSuccessUrl = successUrl || `${baseUrl}/dashboard?subscription=success`
    const finalCancelUrl = cancelUrl || `${baseUrl}/pricing`
    
    // Create checkout session
    const checkoutUrl = await createCheckoutSession({
      userId: session.user.id,
      successUrl: finalSuccessUrl,
      cancelUrl: finalCancelUrl,
      priceId: priceId // Optional, will use default from env
    })
    
    // Log the action
    const ip = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || 
               req.headers['x-real-ip'] as string || 
               'unknown'
    const userAgent = req.headers['user-agent'] || ''
    
    await createAuditLog({
      userId: session.user.id,
      event: 'checkout_initiated',
      metadata: { priceId },
      ip,
      userAgent
    })
    
    return res.status(200).json({ 
      success: true,
      checkoutUrl 
    })
    
  } catch (error) {
    console.error('Checkout session error:', error)
    
    return res.status(500).json({ 
      error: 'Failed to create checkout session' 
    })
  }
}