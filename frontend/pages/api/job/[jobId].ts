import type { NextApiRequest, NextApiResponse } from 'next'
import { API_URL, API_ENDPOINTS } from '../../../constants/api'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ message: 'Method not allowed' })
  }

  const { jobId } = req.query

  if (!jobId || typeof jobId !== 'string') {
    return res.status(400).json({ message: 'Job ID is required' })
  }

  try {
    const endpoint = `${API_URL}${API_ENDPOINTS.jobStatus(jobId)}`
    console.log('[API Proxy] Environment check:', {
      NODE_ENV: process.env.NODE_ENV,
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      API_URL,
      endpoint
    })
    
    // Get job status from backend API using fetch
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    console.log('[API Proxy] Backend response:', response.status, response.statusText)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[API Proxy] Backend error:', response.status, errorText)
      return res.status(response.status).json({ error: errorText })
    }

    const jobData = await response.json()
    console.log('[API Proxy] Success - returning job data')
    res.status(200).json(jobData)
    
  } catch (error) {
    console.error('[API Proxy] Fatal error:', error)
    res.status(500).json({ 
      error: `Proxy error: ${error instanceof Error ? error.message : 'Unknown error'}` 
    })
  }
}