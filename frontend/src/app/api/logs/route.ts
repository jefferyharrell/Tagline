import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    
    // Get backend URL and API key
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';
    const apiKey = process.env.BACKEND_API_KEY || 'dev-api-key-12345';
    
    // Forward the request to the backend with proper authentication
    const response = await fetch(`${backendUrl}/v1/logs/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken.value}`,
        'X-API-Key': apiKey,
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      console.error(`Backend logging request failed: ${response.status}`, error);
      return NextResponse.json(
        { error: error.detail || 'Backend logging request failed' },
        { status: response.status }
      );
    }
    
    const result = await response.json();
    return NextResponse.json(result);
    
  } catch (error) {
    console.error('Error forwarding logs to backend:', error);
    return NextResponse.json(
      { error: 'Failed to process logs' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    service: 'frontend-logging-proxy',
    timestamp: new Date().toISOString()
  });
}