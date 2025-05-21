'use client';

import React, { useState } from 'react';

interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

interface MediaDetailClientProps {
  initialMediaObject: MediaObject;
}

export default function MediaDetailClient({ initialMediaObject }: MediaDetailClientProps) {
  const [mediaObject, setMediaObject] = useState<MediaObject>(initialMediaObject);
  const [isEditing, setIsEditing] = useState(false);
  const [description, setDescription] = useState(mediaObject.metadata.description || '');
  const [keywords, setKeywords] = useState(mediaObject.metadata.keywords?.join(', ') || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    const keywordsArray = keywords
      .split(',')
      .map((keyword) => keyword.trim())
      .filter((keyword) => keyword !== '');

    try {
      const response = await fetch(`/api/media/${mediaObject.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metadata: {
            ...mediaObject.metadata,
            description,
            keywords: keywordsArray,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update media object');
      }

      const updatedMediaObject = await response.json();
      setMediaObject(updatedMediaObject);
      setIsEditing(false);
      setSuccess('Media object updated successfully');
    } catch (err) {
      console.error('Error updating media object:', err);
      setError((err as Error).message || 'Failed to update media object');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      <div>
        <div className="bg-gray-100 rounded-lg overflow-hidden">
          <img
            src={`/api/media/${mediaObject.id}/proxy`}
            alt={mediaObject.metadata.description || 'Media thumbnail'}
            className="object-contain w-full h-full"
          />
        </div>
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-500">Object Key</h3>
          <p className="text-sm text-gray-900 font-mono">{mediaObject.object_key}</p>
        </div>
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-500">Created</h3>
          <p className="text-sm text-gray-900">
            {new Date(mediaObject.created_at).toLocaleString()}
          </p>
        </div>
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-500">Last Updated</h3>
          <p className="text-sm text-gray-900">
            {new Date(mediaObject.updated_at).toLocaleString()}
          </p>
        </div>
      </div>
      <div>
        {error && (
          <div className="mb-4 p-4 rounded-md bg-red-50 text-red-700">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 rounded-md bg-green-50 text-green-700">
            {success}
          </div>
        )}

        {isEditing ? (
          <div>
            <h2 className="text-xl font-bold">Edit Metadata</h2>
            <div className="mt-4">
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700"
              >
                Description
              </label>
              <textarea
                id="description"
                name="description"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            <div className="mt-4">
              <label
                htmlFor="keywords"
                className="block text-sm font-medium text-gray-700"
              >
                Keywords (comma-separated)
              </label>
              <input
                type="text"
                id="keywords"
                name="keywords"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            <div className="mt-6 flex space-x-3">
              <button
                type="button"
                onClick={handleSave}
                disabled={isLoading}
                className="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                {isLoading ? 'Saving...' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsEditing(false);
                  setDescription(mediaObject.metadata.description || '');
                  setKeywords(mediaObject.metadata.keywords?.join(', ') || '');
                }}
                disabled={isLoading}
                className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Metadata</h2>
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Edit
              </button>
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-500">Description</h3>
              <p className="text-sm text-gray-900">
                {mediaObject.metadata.description || 'No description provided'}
              </p>
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-500">Keywords</h3>
              <div className="mt-1 flex flex-wrap gap-1">
                {mediaObject.metadata.keywords?.map((keyword, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700"
                  >
                    {keyword}
                  </span>
                ))}
                {(!mediaObject.metadata.keywords || mediaObject.metadata.keywords.length === 0) && (
                  <p className="text-sm text-gray-500">No keywords</p>
                )}
              </div>
            </div>
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-500">All Metadata</h3>
              <pre className="mt-1 p-4 bg-gray-50 rounded-md overflow-auto text-xs">
                {JSON.stringify(mediaObject.metadata, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
