import React from 'react';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import Link from 'next/link';
import MediaDetailClient from './media-detail-client';

// This will handle fetching the media object on the server side
async function getMediaObject(mediaId: string) {
  const cookieStore = await cookies();
  const authToken = cookieStore.get('auth_token');

  if (!authToken) {
    return null;
  }

  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const backendApiKey = process.env.BACKEND_API_KEY;

  try {
    const response = await fetch(`${backendUrl}/v1/media/${mediaId}`, {
      headers: {
        'Authorization': `Bearer ${authToken.value}`,
        'X-API-Key': backendApiKey || '',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching media object:', error);
    return null;
  }
}

export default async function MediaDetailPage({ params }: { params: { id: string } }) {
  // Await both dynamic APIs
  const cookieStore = await cookies();
  const { id } = await params;
  const authToken = cookieStore.get('auth_token');

  if (!authToken) {
    redirect('/');
  }

  const mediaObject = await getMediaObject(id);

  if (!mediaObject) {
    redirect('/media');
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Media Details</h1>
          <nav className="flex space-x-4">
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
              Dashboard
            </Link>
            <Link href="/media" className="text-gray-600 hover:text-gray-900">
              Gallery
            </Link>
          </nav>
        </div>
      </header>
      <main>
        <div className="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
          <div className="bg-white p-8 rounded-lg shadow">
            <div className="mb-6">
              <Link href="/media" className="text-indigo-600 hover:text-indigo-800">
                &larr; Back to Gallery
              </Link>
            </div>
            <MediaDetailClient initialMediaObject={mediaObject} />
          </div>
        </div>
      </main>
    </div>
  );
}
