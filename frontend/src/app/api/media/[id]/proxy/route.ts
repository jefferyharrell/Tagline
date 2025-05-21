import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Get the auth token from cookies
    const cookieStore = cookies();
    const authToken = cookieStore.get('auth_token');

    if (!authToken) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const id = params.id;
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const backendApiKey = process.env.BACKEND_API_KEY;

    const response = await fetch(`${backendUrl}/v1/media/${id}/proxy`, {
      headers: {
        'Authorization': `Bearer ${authToken.value}`,
        'X-API-Key': backendApiKey || '',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.detail || 'Failed to fetch proxy' },
        { status: response.status }
      );
    }

    // Get the proxy data as an array buffer
    const proxyBuffer = await response.arrayBuffer();
    const contentType = response.headers.get('content-type') || 'image/jpeg';

    // Return the proxy as a response with the proper content type
    return new NextResponse(proxyBuffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400',
      },
    });
  } catch (error) {
    console.error('Error fetching proxy:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
