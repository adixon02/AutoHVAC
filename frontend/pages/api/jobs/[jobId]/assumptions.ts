import { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { jobId } = req.query
  const { duct_config, heating_fuel } = req.body

  try {
    // Forward the request to the backend
    const backendResponse = await fetch(`http://localhost:8000/api/v1/blueprint/jobs/${jobId}/assumptions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        duct_config,
        heating_fuel,
      }),
    })

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json()
      return res.status(backendResponse.status).json(errorData)
    }

    const result = await backendResponse.json()
    res.status(200).json(result)
  } catch (error) {
    console.error('Error submitting assumptions:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}