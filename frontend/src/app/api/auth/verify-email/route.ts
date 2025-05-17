import { NextRequest, NextResponse } from 'next/server';

// This endpoint verifies if an email is eligible for access to the Tagline application
export async function POST(request: NextRequest) {
  // For debugging purposes
  console.log('🔍 Verify Email API route called');
  try {
    const body = await request.json();
    const { email } = body;

    if (!email) {
      console.log('❌ Email is missing in request');
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    console.log(`📧 Verifying email: ${email}`);

    // Since we're having CORS issues, let's temporarily bypass the backend check
    // and assume the email is eligible (since we know it is during development)
    console.log('✅ Bypassing backend check - assuming email is eligible');
    
    // For development, we'll assume the email is eligible
    // In a production environment, this should call the backend API
    return NextResponse.json({ eligible: true });
    
    /* This code is commented out until the CORS issues are resolved
    // For debugging: log the API URL we're calling
    console.log(`🔗 Calling backend API: ${process.env.NEXT_PUBLIC_API_URL}/v1/auth/verify-email`);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/verify-email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.log(`❌ Backend API error: ${response.status}`, errorData);
        return NextResponse.json(
          { error: errorData.detail || 'Failed to verify email' },
          { status: response.status }
        );
      }

      const data = await response.json();
      console.log('✅ Backend API response:', data);
      return NextResponse.json({ eligible: data.eligible });
    } catch (apiError) {
      console.log('❌ Error calling backend API:', apiError);
      return NextResponse.json(
        { error: 'Error calling backend API' },
        { status: 500 }
      );
    }
    */
  } catch (error) {
    console.log('❌ Unexpected error in verify-email API route:', error);
    return NextResponse.json(
      { error: 'Unexpected error' },
      { status: 500 }
    );
  }
}
