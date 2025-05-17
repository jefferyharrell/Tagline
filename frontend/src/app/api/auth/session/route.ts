import { NextRequest, NextResponse } from 'next/server';

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

    // Log the token for debugging
    console.log('Received token in session endpoint:', token.substring(0, 10) + '...');

    try {
      // The backend expects a specific format for the Stytch token
      // We need to send the token to the backend's authenticate endpoint
      console.log('Calling backend authenticate endpoint');
      
      // First, authenticate with the backend using the Stytch token
      const authResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/authenticate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token: token,
          session_token: token
        })
      });
      
      if (!authResponse.ok) {
        const errorText = await authResponse.text();
        console.error('Backend authentication failed:', errorText);
        return NextResponse.json(
          { error: 'Authentication failed with backend' },
          { status: authResponse.status }
        );
      }
      
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
      console.error('Error authenticating with backend:', error);
      return NextResponse.json(
        { error: 'Failed to authenticate with backend' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Session API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
