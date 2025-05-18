import { NextRequest, NextResponse } from 'next/server';
import { loadStytch } from '@/lib/stytch-server';
import { redirect } from 'next/navigation';

export async function GET(request: NextRequest) {
  try {
    // Get token from URL params for Stytch redirects
    const searchParams = request.nextUrl.searchParams;
    const token = searchParams.get('token');
    
    console.log('Processing auth callback with token:', token ? 'Token present' : 'No token');
    
    if (!token) {
      return NextResponse.json(
        { message: 'Missing authentication token' },
        { status: 400 }
      );
    }
    
    // Call backend directly with the token - backend will handle Stytch verification
    console.log('Calling backend to authenticate user with token');
    console.log('Backend URL:', process.env.BACKEND_URL);
    
    const backendResponse = await fetch(`${process.env.BACKEND_URL}/v1/auth/authenticate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BACKEND_API_KEY || '',
      },
      body: JSON.stringify({
        token: token
      }),
    });
    
    if (!backendResponse.ok) {
      console.error('Backend authentication failed with status:', backendResponse.status);
      let errorMessage = 'Authentication failed';
      try {
        const errorData = await backendResponse.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
        console.error('Backend error details:', errorData);
      } catch (e) {
        console.error('Could not parse backend error response');
      }
      return redirect(`/?error=${encodeURIComponent(errorMessage)}`);
    }
    
    const userResponse = await backendResponse.json();
    
    // 3. Set JWT in HTTP-only cookie
    const response = NextResponse.redirect(new URL('/dashboard', request.url));
    
    response.cookies.set({
      name: 'auth_token',
      value: userResponse.access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7, // 1 week
    });
    
    return response;
    
  } catch (error) {
    console.error('Authentication error:', error);
    // Redirect to login with error
    const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
    return redirect(`/?error=${encodeURIComponent(errorMessage)}`);
  }
}

export async function POST(request: NextRequest) {
  try {
    const { token } = await request.json();
    
    if (!token) {
      return NextResponse.json(
        { message: 'Missing authentication token' },
        { status: 400 }
      );
    }
    
    // Call backend directly with the token - backend will handle Stytch verification
    const backendResponse = await fetch(`${process.env.BACKEND_URL}/v1/auth/authenticate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BACKEND_API_KEY || '',
      },
      body: JSON.stringify({
        token: token
      }),
    });
    
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      return NextResponse.json(
        { message: errorData.detail || errorData.message || 'Authentication failed' },
        { status: backendResponse.status }
      );
    }
    
    const userResponse = await backendResponse.json();
    
    // 3. Create response with JWT
    const response = NextResponse.json({
      success: true,
      user: {
        id: userResponse.user_id,
        email: userResponse.email,
        roles: userResponse.roles
      },
      session: {
        jwt: userResponse.access_token
      }
    });
    
    // 4. Set JWT in HTTP-only cookie
    response.cookies.set({
      name: 'auth_token',
      value: userResponse.access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7, // 1 week
    });
    
    return response;
    
  } catch (error) {
    console.error('Authentication error:', error);
    return NextResponse.json(
      { message: 'Authentication failed' },
      { status: 500 }
    );
  }
}
