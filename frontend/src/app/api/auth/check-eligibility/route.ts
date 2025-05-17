import { NextRequest, NextResponse } from 'next/server';

// This would typically connect to your backend API to check if the email is eligible
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    // Call your backend API to check if the email is eligible
    // For now, we'll use a simple mock implementation
    // In production, this should call your actual backend API
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
      return NextResponse.json(
        { error: errorData.detail || 'Failed to check eligibility' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json({ eligible: data.eligible });
  } catch (error) {
    console.error('Error checking eligibility:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
