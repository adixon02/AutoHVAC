import { NextApiRequest, NextApiResponse } from 'next'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
})

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { sessionId } = req.query

  if (!sessionId || typeof sessionId !== 'string') {
    return res.status(400).json({ error: 'Session ID is required' })
  }

  try {
    const session = await stripe.checkout.sessions.retrieve(sessionId)
    
    return res.status(200).json({
      customer_email: session.customer_email || session.customer_details?.email,
      payment_status: session.payment_status,
      subscription: session.subscription,
    })
  } catch (error) {
    console.error('Error retrieving Stripe session:', error)
    return res.status(500).json({ error: 'Failed to retrieve session' })
  }
}