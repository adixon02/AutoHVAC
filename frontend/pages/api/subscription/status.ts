import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '../auth/[...nextauth]'

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
    
    // Get backend JWT token
    const accessToken = (session as any).accessToken
    if (!accessToken) {
      return res.status(401).json({ error: 'No backend authentication token' })
    }
    
    // Call backend subscription status endpoint
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${backendUrl}/api/v1/billing/subscription-status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    })
    
    if (!response.ok) {
      const error = await response.json()
      return res.status(response.status).json(error)
    }
    
    const data = await response.json()
    return res.status(200).json(data)
    
  } catch (error) {
    console.error('Subscription status error:', error)
    return res.status(500).json({ 
      error: 'Failed to fetch subscription status' 
    })
  }
}