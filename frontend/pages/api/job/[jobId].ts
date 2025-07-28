import type { NextApiRequest, NextApiResponse } from 'next'
import axios from 'axios'
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
    console.log('[API Proxy] Getting job status:', endpoint)
    
    // Get job status from v1 API
    const statusResponse = await axios.get(endpoint)

    // v1 API returns the complete job status with results
    const jobData = statusResponse.data

    res.status(200).json(jobData)
  } catch (error) {
    console.error('Job status proxy error:', error)
    if (axios.isAxiosError(error) && error.response) {
      res.status(error.response.status).json(error.response.data)
    } else {
      res.status(500).json({ message: 'Internal server error' })
    }
  }
}