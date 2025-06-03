import { NextRequest, NextResponse } from 'next/server';
import { cookies } from "next/headers";

export async function GET(request: NextRequest) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const path = searchParams.get('path');
    const limit = searchParams.get('limit');
    const offset = searchParams.get('offset');
    
    // Build backend URL
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';
    const url = new URL(`${backendUrl}/v1/storage/browse`);
    
    if (path) {
      url.searchParams.set('path', path);
    }
    if (limit) {
      url.searchParams.set('limit', limit);
    }
    if (offset) {
      url.searchParams.set('offset', offset);
    }

    // Forward the request to the backend
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken.value}`,
        'X-API-Key': process.env.BACKEND_API_KEY || '',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend browse request failed:', response.status, errorText);
      return NextResponse.json(
        { error: 'Failed to fetch browse data' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Browse API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}