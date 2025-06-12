import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function GET() {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('auth_token')

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000'
    const apiKey = process.env.BACKEND_API_KEY || ''

    const response = await fetch(`${backendUrl}/v1/admin/ingest/status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token.value}`,
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', response.status, errorText)
      return NextResponse.json(
        { error: 'Failed to fetch ingest status' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching ingest status:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}