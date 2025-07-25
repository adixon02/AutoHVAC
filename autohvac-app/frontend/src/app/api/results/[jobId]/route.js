export const runtime = 'nodejs';

export async function GET(request, { params }) {
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'https://autohvac.onrender.com';
  const { jobId } = params;
  
  if (!BACKEND) {
    return new Response(
      JSON.stringify({ error: 'Backend URL not configured' }), 
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  try {
    // Forward the request to the backend
    const backendRes = await fetch(`${BACKEND}/api/v2/blueprint/results/${jobId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Get response body
    const responseBody = await backendRes.text();
    
    // Copy headers from backend response, excluding problematic ones
    const responseHeaders = {};
    backendRes.headers.forEach((value, key) => {
      if (!['connection', 'transfer-encoding', 'content-encoding'].includes(key.toLowerCase())) {
        responseHeaders[key] = value;
      }
    });

    return new Response(responseBody, {
      status: backendRes.status,
      headers: responseHeaders,
    });
    
  } catch (error) {
    console.error('Results proxy error:', error);
    return new Response(
      JSON.stringify({ 
        error: 'Results request failed', 
        details: error.message 
      }), 
      { 
        status: 500, 
        headers: { 'Content-Type': 'application/json' } 
      }
    );
  }
}