import { NextRequest, NextResponse } from 'next/server';
import { getCurrentUser } from '@/lib/jwt-utils';

export async function GET(request: NextRequest) {
  try {
    // Get user info from JWT in cookies
    const user = await getCurrentUser(request);
    
    if (!user) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Get the JWT token from the cookie
    const token = request.cookies.get('auth_token')?.value;
    
    if (!token) {
      return NextResponse.json(
        { error: 'No auth token found' },
        { status: 401 }
      );
    }

    // Call backend /auth/me endpoint to get full user data
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/v1/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-API-Key': process.env.BACKEND_API_KEY || '',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch user data');
    }

    const userData = await response.json();
    return NextResponse.json(userData);
  } catch (error) {
    console.error('Error fetching user data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch user data' },
      { status: 500 }
    );
  }
}

// Allow updating user info
export async function PATCH(request: NextRequest) {
  try {
    const user = await getCurrentUser(request);
    
    if (!user) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = await request.json();
    
    // Get the JWT token from the cookie
    const token = request.cookies.get('auth_token')?.value;
    
    if (!token) {
      return NextResponse.json(
        { error: 'No auth token found' },
        { status: 401 }
      );
    }
    
    // Call backend /auth/me endpoint to update user data
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/v1/auth/me`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-API-Key': process.env.BACKEND_API_KEY || '',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error('Failed to update user data');
    }

    const userData = await response.json();
    return NextResponse.json(userData);
  } catch (error) {
    console.error('Error updating user data:', error);
    return NextResponse.json(
      { error: 'Failed to update user data' },
      { status: 500 }
    );
  }
}