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

    // For debugging: log the API URL we're calling
    console.log(`🔗 Calling backend API: ${process.env.NEXT_PUBLIC_API_URL}/v1/auth/verify-email`);

    // Call the actual backend API to verify the email
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/verify-email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.API_KEY || '',
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
      console.error('❌ API request error:', apiError);
      return NextResponse.json(
        { error: 'Failed to communicate with backend API' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('❌ Error verifying email:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
