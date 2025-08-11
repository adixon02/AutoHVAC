import { NextApiRequest, NextApiResponse } from 'next'

// This webhook endpoint is deprecated - the backend handles all Stripe webhooks
// We keep this endpoint to avoid 404 errors if Stripe still has it configured
// Configure your Stripe webhook to point to: https://your-backend-url/api/v1/billing/webhook

export const config = {
  api: {
    bodyParser: false,
  },
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }
  
  console.log('Frontend webhook called - this is deprecated. Configure Stripe to use the backend webhook URL instead.')
  
  // Always return 200 to acknowledge receipt
  // This prevents Stripe from retrying
  return res.status(200).json({ 
    received: true,
    message: 'Webhook acknowledged. Please configure Stripe to use the backend webhook URL.' 
  })
}