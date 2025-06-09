import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const BACKEND_API_KEY = process.env.BACKEND_API_KEY || '';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth_token');

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/v1/auth/users/export`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token.value}`,
        'X-API-Key': BACKEND_API_KEY,
      },
    });

    if (!response.ok) {
      const errorData = await response.text();
      console.error('Backend error:', errorData);
      return NextResponse.json(
        { error: 'Failed to export users' },
        { status: response.status }
      );
    }

    // Get the CSV content and filename from the backend response
    const csvContent = await response.text();
    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = contentDisposition?.match(/filename=(.+)/)?.[1] || 'users.csv';

    // Return the CSV with proper headers
    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename=${filename}`,
      },
    });
  } catch (error) {
    console.error('Export error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}