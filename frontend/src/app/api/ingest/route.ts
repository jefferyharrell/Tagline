import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export async function POST(request: NextRequest) {
  try {
    // Get the auth token from cookies
    const cookieStore = cookies();
    const authToken = cookieStore.get('auth_token');

    if (!authToken) {
      return NextResponse.redirect(new URL('/', request.url));
    }

    // Call the backend API to trigger ingest task
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const backendApiKey = process.env.BACKEND_API_KEY;

    const response = await fetch(`${backendUrl}/v1/tasks/ingest`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken.value}`,
        'X-API-Key': backendApiKey || '',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // If there's an error, redirect back to dashboard with error parameter
      const error = await response.json();
      const errorMessage = encodeURIComponent(
        error.detail || 'Failed to start ingest task'
      );
      return NextResponse.redirect(
        new URL(`/dashboard?error=${errorMessage}`, request.url)
      );
    }

    // On success, redirect back to dashboard with success message
    return NextResponse.redirect(
      new URL('/dashboard?success=Ingest task started successfully', request.url)
    );
  } catch (error) {
    console.error('Error starting ingest task:', error);
    // On exception, redirect back to dashboard with error
    const errorMessage = encodeURIComponent('Internal server error');
    return NextResponse.redirect(
      new URL(`/dashboard?error=${errorMessage}`, request.url)
    );
  }
}
