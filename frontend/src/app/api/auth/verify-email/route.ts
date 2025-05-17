import { NextRequest, NextResponse } from 'next/server';

// This endpoint verifies if an email is eligible for access to the Tagline application
export async function POST(request: NextRequest) {
  try {
    // Parse the incoming request
    const body = await request.json();
    const { email } = body;

    // Validate the request
    if (!email) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    // Get the backend URL from environment variables
    const backendUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!backendUrl) {
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    // Construct the full URL for the backend API
    const apiUrl = `${backendUrl}/v1/auth/verify-email`;

    try {
      // Forward the request to the backend
      const startTime = Date.now();
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.API_KEY && { 'Authorization': `Bearer ${process.env.API_KEY}` })
        },
        body: JSON.stringify({ email }),
      });

      const responseTime = Date.now() - startTime;

      // Get the response data
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        throw new Error('Invalid response from backend');
      }

      // Forward the backend response to the client
      return NextResponse.json(data, { status: response.status });

    } catch (apiError) {
      const errorMessage = apiError instanceof Error ? apiError.message : 'An unknown error occurred';
      return NextResponse.json(
        { error: 'Error connecting to the server', details: errorMessage },
        { status: 502 } // Bad Gateway
      );
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json(
      {
        error: 'An unexpected error occurred',
        details: process.env.NODE_ENV === 'development' ? errorMessage : undefined
      },
      { status: 500 }
    );
  }
}
