import { cookies } from 'next/headers'

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')

  if (!token) {
    return new Response('Unauthorized', { status: 401 })
  }

  const backendUrl = process.env.BACKEND_URL || 'http://backend:8000'
  const apiKey = process.env.BACKEND_API_KEY || ''

  try {
    const response = await fetch(`${backendUrl}/v1/events/orchestrator`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token.value}`,
        'X-API-Key': apiKey,
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    })

    if (!response.ok) {
      return new Response('Failed to connect to orchestrator event stream', { 
        status: response.status 
      })
    }

    // Stream the response from backend to frontend
    return new Response(response.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
      },
    })
  } catch (error) {
    console.error('Error connecting to orchestrator event stream:', error)
    return new Response('Internal server error', { status: 500 })
  }
}