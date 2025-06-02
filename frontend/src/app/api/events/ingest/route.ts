
import { cookies } from "next/headers";

export async function GET() {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return new Response('Unauthorized', { status: 401 });
    }

    // Build backend URL
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';
    const url = `${backendUrl}/v1/events/ingest`;

    // Forward the request to the backend
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken.value}`,
        'X-API-Key': process.env.BACKEND_API_KEY || '',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    });

    if (!response.ok) {
      console.error('Backend SSE request failed:', response.status);
      return new Response('Failed to connect to event stream', { status: response.status });
    }

    // Stream the response back to the client
    return new Response(response.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
      },
    });
  } catch (error) {
    console.error('SSE proxy error:', error);
    return new Response('Internal server error', { status: 500 });
  }
}