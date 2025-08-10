import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '../auth/[...nextauth]'
import { getUserSubscription, hasActiveSubscription } from '@/lib/stripe'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }
  
  try {
    // Get session
    const session = await getServerSession(req, res, authOptions)
    
    if (!session?.user?.id) {
      return res.status(401).json({ error: 'Unauthorized' })
    }
    
    // Get subscription status
    const hasSubscription = await hasActiveSubscription(session.user.id)
    const subscriptionDetails = await getUserSubscription(session.user.id)
    
    return res.status(200).json({
      hasActiveSubscription: hasSubscription,
      details: subscriptionDetails
    })
    
  } catch (error) {
    console.error('Subscription status error:', error)
    return res.status(500).json({ 
      error: 'Failed to fetch subscription status' 
    })
  }
}