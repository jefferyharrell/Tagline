"use client";

import React, { useState, useEffect } from "react";
import PhotoThumbnail from "@/components/PhotoThumbnail";
import { MediaObject } from "@/types/media";

interface ComponentTestData {
  realMedia: MediaObject[];
  loading: boolean;
  error: string | null;
}

export default function ComponentsTestPage() {
  const [data, setData] = useState<ComponentTestData>({
    realMedia: [],
    loading: true,
    error: null,
  });

  // Fetch real media data for testing
  useEffect(() => {
    const fetchMediaData = async () => {
      try {
        const response = await fetch("/api/library?limit=20");
        if (response.ok) {
          const result = await response.json();
          setData({
            realMedia: result.media_objects || [],
            loading: false,
            error: null,
          });
        } else {
          setData({
            realMedia: [],
            loading: false,
            error: `Failed to fetch: ${response.status}`,
          });
        }
      } catch (err) {
        setData({
          realMedia: [],
          loading: false,
          error: err instanceof Error ? err.message : "Unknown error",
        });
      }
    };

    fetchMediaData();
  }, []);

  // Mock data for different states
  const mockMediaStates: MediaObject[] = [
    {
      object_key: "test/pending-photo.jpg",
      ingestion_status: "pending",
      has_thumbnail: false,
      has_proxy: false,
      metadata: {
        description: "Pending ingestion photo",
      },
    },
    {
      object_key: "test/processing-photo.jpg",
      ingestion_status: "processing",
      has_thumbnail: false,
      has_proxy: false,
      metadata: {
        description: "Currently processing photo",
      },
    },
    {
      object_key: "test/completed-no-thumb.jpg",
      ingestion_status: "completed",
      has_thumbnail: false,
      has_proxy: true,
      metadata: {
        description: "Completed but no thumbnail available",
      },
    },
    {
      object_key: "test/failed-photo.jpg",
      ingestion_status: "failed",
      has_thumbnail: false,
      has_proxy: false,
      metadata: {
        description: "Failed ingestion photo",
      },
    },
  ];

  const handlePhotoClick = (media: MediaObject) => {
    alert(`Clicked photo: ${media.object_key}\nStatus: ${media.ingestion_status}\nDescription: ${media.metadata?.description || "No description"}`);
  };

  if (data.loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Component Test Page</h1>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
              <div className="h-32 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Component Test Page</h1>
        
        {/* PhotoThumbnail Component Tests */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">PhotoThumbnail Component</h2>
          
          {data.error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
              <div className="text-red-600 text-sm">
                Error loading real data: {data.error}
              </div>
            </div>
          )}

          {/* Mock States Section */}
          <div className="mb-8">
            <h3 className="text-lg font-medium text-gray-700 mb-4">Mock States (Testing Different Conditions)</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {mockMediaStates.map((media) => (
                <div key={media.object_key} className="space-y-2">
                  <div className="w-32 h-32">
                    <PhotoThumbnail
                      media={media}
                      onClick={handlePhotoClick}
                      className="w-full h-full"
                    />
                  </div>
                  <div className="text-xs text-gray-600 text-center">
                    <div className="font-medium">{media.ingestion_status}</div>
                    <div>Has thumbnail: {media.has_thumbnail ? "Yes" : "No"}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Real Data Section */}
          {data.realMedia.length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-medium text-gray-700 mb-4">
                Real Data from API ({data.realMedia.length} items)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                {data.realMedia.slice(0, 16).map((media) => (
                  <div key={media.object_key} className="space-y-2">
                    <div className="w-24 h-24">
                      <PhotoThumbnail
                        media={media}
                        onClick={handlePhotoClick}
                        className="w-full h-full"
                      />
                    </div>
                    <div className="text-xs text-gray-600 text-center">
                      <div className="font-medium truncate" title={media.object_key}>
                        {media.object_key.split('/').pop()}
                      </div>
                      <div>{media.ingestion_status}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Custom Styling Examples */}
          <div className="mb-8">
            <h3 className="text-lg font-medium text-gray-700 mb-4">Custom Styling Examples</h3>
            <div className="grid grid-cols-3 gap-4">
              {data.realMedia.slice(0, 3).map((media, index) => {
                const customClasses = [
                  "border-2 border-blue-200 rounded-lg",
                  "border-2 border-green-200 rounded-md",
                  "border-4 border-purple-300 rounded-xl",
                ];
                
                return (
                  <div key={`custom-${media.object_key}`} className="space-y-2">
                    <div className="w-32 h-32">
                      <PhotoThumbnail
                        media={media}
                        onClick={handlePhotoClick}
                        className={`w-full h-full ${customClasses[index]}`}
                      />
                    </div>
                    <div className="text-xs text-gray-600 text-center">
                      Custom styling #{index + 1}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Grid Layout Example */}
          <div>
            <h3 className="text-lg font-medium text-gray-700 mb-4">Grid Layout Example</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
              {data.realMedia.slice(0, 12).map((media) => (
                <div key={`grid-${media.object_key}`} className="w-32 h-32">
                  <PhotoThumbnail
                    media={media}
                    onClick={handlePhotoClick}
                    className="w-full h-full"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Future Components Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Future Components</h2>
          <div className="text-gray-600">
            <p>This section will showcase additional custom components as they are developed:</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>MediaGrid component</li>
              <li>SearchBar component</li>
              <li>MediaCard component</li>
              <li>LoadingStates component</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}