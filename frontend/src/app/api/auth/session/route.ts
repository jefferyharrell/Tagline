import { NextRequest, NextResponse } from 'next/server';

// Helper function to authenticate with the backend using the magic link token
async function authenticateWithBackend(token: string) {
  console.log('Authenticating with backend using magic link token:', token.substring(0, 10) + '...');
  
  const authResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/authenticate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      token: token // This is the raw magic link token
    })
  });
  
  if (!authResponse.ok) {
    const errorText = await authResponse.text();
    console.error('Backend authentication failed:', errorText);
    throw new Error(`Backend authentication failed: ${errorText}`);
  }
  
  return authResponse;
}

export async function GET(request: NextRequest) {
  try {
    // Get the authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    // Extract the token
    const token = authHeader.substring(7);
    if (!token) {
      return NextResponse.json(
        { error: 'Missing token' },
        { status: 401 }
      );
    }

    console.log('GET /api/auth/session - Received token in session endpoint:', token.substring(0, 10) + '...');

    try {
      // Authenticate with the backend using the provided token
      const authResponse = await authenticateWithBackend(token);
      
      // Get the access token from the authentication response
      const authData = await authResponse.json();
      console.log('Backend auth successful, received token type:', authData.token_type);
      
      // Get the access token and user roles
      const accessToken = authData.access_token;
      const userRoles = authData.user_roles || [];
      
      // Use the access token to get user data
      const userResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      if (!userResponse.ok) {
        const errorText = await userResponse.text();
        console.error('Failed to get user data:', errorText);
        return NextResponse.json(
          { error: 'Failed to get user data' },
          { status: userResponse.status }
        );
      }
      
      // Parse the user data
      const userData = await userResponse.json();
      console.log('Received user data from backend');
      
      // Return the user data in the format expected by our frontend
      return NextResponse.json({
        user: {
          id: userData.id,
          email: userData.email,
          roles: userRoles,
          firstName: userData.first_name,
          lastName: userData.last_name,
          createdAt: userData.created_at,
          lastLoginAt: new Date().toISOString()
        }
      });
    } catch (error) {
      console.error('Error in GET /api/auth/session:', error);
      return NextResponse.json(
        { error: error instanceof Error ? error.message : 'Failed to authenticate with backend' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Unexpected error in session API:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Handle POST requests to create a session with a magic link token
export async function POST(request: NextRequest) {
  try {
    // Parse the request body
    const body = await request.json();
    const { token } = body;
    
    if (!token) {
      return NextResponse.json(
        { error: 'No token provided in request body' },
        { status: 400 }
      );
    }
    
    console.log('POST /api/auth/session - Creating session with magic link token:', token.substring(0, 10) + '...');
    
    try {
      // Call the backend directly to authenticate with the token
      console.log('Calling backend directly with magic link token');
      
      const backendResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/authenticate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token: token // This is the raw magic link token
        })
      });
      
      if (!backendResponse.ok) {
        const errorText = await backendResponse.text();
        console.error('Backend authentication failed:', errorText);
        return NextResponse.json(
          { error: `Backend authentication failed: ${errorText}` },
          { status: backendResponse.status }
        );
      }
      
      // Get the access token from the response
      const authData = await backendResponse.json();
      console.log('Backend auth successful with token type:', authData.token_type);
      
      // Return the session data
      return NextResponse.json({
        session_token: authData.access_token,
        user_id: authData.user_id,
        roles: authData.user_roles || []
      });
      
    } catch (error) {
      console.error('Error creating session with magic link token:', error);
      return NextResponse.json(
        { error: error instanceof Error ? error.message : 'Failed to create session' },
        { status: 500 }
      );
    }
    
  } catch (error) {
    console.error('Unexpected error in session creation:', error);
    return NextResponse.json(
      { error: 'Internal server error during authentication' },
      { status: 500 }
    );
  }
}
