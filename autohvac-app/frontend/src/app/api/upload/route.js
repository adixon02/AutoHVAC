export const runtime = 'nodejs';

export const config = {
  api: { 
    bodyParser: false, 
    sizeLimit: '200mb' 
  },
};

export async function POST(request) {
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'https://autohvac.onrender.com';
  
  if (!BACKEND) {
    return new Response(
      JSON.stringify({ error: 'Backend URL not configured' }), 
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  try {
    // Get the FormData from the request
    const formData = await request.formData();
    
    // Create headers object, excluding problematic ones
    const headers = {};
    request.headers.forEach((value, key) => {
      if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        headers[key] = value;
      }
    });

    // Forward the request to the backend
    const backendRes = await fetch(`${BACKEND}/api/v2/blueprint/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    // Create response with same status
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
    console.error('Proxy error:', error);
    return new Response(
      JSON.stringify({ 
        error: 'Proxy request failed', 
        details: error.message 
      }), 
      { 
        status: 500, 
        headers: { 'Content-Type': 'application/json' } 
      }
    );
  }
}

export async function OPTIONS(request) {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    },
  });
}