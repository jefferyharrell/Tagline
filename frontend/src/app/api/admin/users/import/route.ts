import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const BACKEND_API_KEY = process.env.BACKEND_API_KEY || '';

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth_token');

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get the form data from the request
    const formData = await request.formData();

    // Forward the form data to the backend
    const backendFormData = new FormData();
    const file = formData.get('file') as File;
    if (file) {
      backendFormData.append('file', file);
    }

    const response = await fetch(`${BACKEND_URL}/v1/auth/users/import`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token.value}`,
        'X-API-Key': BACKEND_API_KEY,
      },
      body: backendFormData,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Import error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}