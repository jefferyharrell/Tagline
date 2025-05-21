import { NextRequest, NextResponse } from 'next/server';

// Only available in development mode
export async function POST(request: NextRequest) {
  console.log('Dev login API route called');
  try {
    // Security checks
    console.log('NODE_ENV:', process.env.NODE_ENV);
    console.log('AUTH_BYPASS_ENABLED:', process.env.NEXT_PUBLIC_AUTH_BYPASS_ENABLED);
    console.log('BACKEND_URL:', process.env.BACKEND_URL);
    console.log('BACKEND_API_KEY:', process.env.BACKEND_API_KEY ? '[SET]' : '[NOT SET]');
    
    if (process.env.NODE_ENV === 'production') {
      return NextResponse.json(
        { message: 'Dev login not available in production' },
        { status: 403 }
      );
    }

    if (process.env.NEXT_PUBLIC_AUTH_BYPASS_ENABLED !== 'true') {
      return NextResponse.json(
        { message: 'Auth bypass not enabled' },
        { status: 403 }
      );
    }

    // Get email from request
    const { email } = await request.json();
    
    if (!email) {
      return NextResponse.json(
        { message: 'Email is required' },
        { status: 400 }
      );
    }

    // Call backend bypass endpoint
    const backendUrl = `${process.env.BACKEND_URL}/v1/auth/bypass`;
    console.log('Calling backend at:', backendUrl);
    
    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BACKEND_API_KEY || '',
      },
      body: JSON.stringify({ email }),
    });
    
    if (!backendResponse.ok) {
      console.log('Backend response not OK:', backendResponse.status);
      let errorMessage = 'Authentication failed';
      try {
        const errorData = await backendResponse.json();
        console.log('Backend error data:', errorData);
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        console.error('Could not parse backend error response');
      }
      return NextResponse.json(
        { message: errorMessage },
        { status: backendResponse.status }
      );
    }
    
    const userResponse = await backendResponse.json();
    
    // Create response
    const response = NextResponse.json({
      success: true,
      message: 'Development login successful',
    });
    
    // Set JWT in HTTP-only cookie
    response.cookies.set({
      name: 'auth_token',
      value: userResponse.access_token,
      httpOnly: true,
      secure: false, // For development
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7, // 1 week
    });
    
    return response;
    
  } catch (error) {
    console.error('Dev login error:', error);
    return NextResponse.json(
      { message: 'Development login failed' },
      { status: 500 }
    );
  }
}
