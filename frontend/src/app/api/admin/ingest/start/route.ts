import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('auth_token')

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000'
    const apiKey = process.env.BACKEND_API_KEY || ''

    const response = await fetch(`${backendUrl}/v1/admin/ingest/start`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token.value}`,
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error starting ingest:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}