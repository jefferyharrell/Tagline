"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import MediaThumbnail from "@/components/MediaThumbnail";
import { Skeleton } from "@/components/ui/skeleton";

interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

interface PaginatedResponse {
  items: MediaObject[];
  total: number;
  limit: number;
  offset: number;
}

export default function GalleryClient() {
  const [mediaObjects, setMediaObjects] = useState<MediaObject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadingRef = useRef<HTMLDivElement>(null);

  const ITEMS_PER_PAGE = 36;

  const fetchMediaObjects = useCallback(
    async (reset: boolean = false) => {
      if (isLoading || (!hasMore && !reset)) return;

      const currentOffset = reset ? 0 : offset;
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/library?limit=${ITEMS_PER_PAGE}&offset=${currentOffset}`,
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || "Failed to fetch media objects");
        }

        const data: PaginatedResponse = await response.json();

        // Ensure each media object has a metadata field
        const sanitizedItems = data.items.map((item) => ({
          ...item,
          metadata: item.metadata || {},
        }));

        if (reset) {
          setMediaObjects(sanitizedItems);
        } else {
          setMediaObjects((prev) => [...prev, ...sanitizedItems]);
        }

        // Check if we've loaded all items
        setHasMore(currentOffset + data.items.length < data.total);
        setOffset(currentOffset + data.items.length);
        setInitialLoad(false);
      } catch (err) {
        console.error("Error fetching media objects:", err);
        setError((err as Error).message || "Failed to fetch media objects");
      } finally {
        setIsLoading(false);
      }
    },
    [offset, isLoading, hasMore],
  );

  // Initialize data load
  useEffect(() => {
    fetchMediaObjects(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Setup intersection observer for infinite scroll
  useEffect(() => {
    if (loadingRef.current && !initialLoad) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          const [entry] = entries;
          if (entry.isIntersecting && hasMore && !isLoading) {
            fetchMediaObjects();
          }
        },
        { threshold: 0.5 },
      );

      observerRef.current.observe(loadingRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [fetchMediaObjects, hasMore, isLoading, initialLoad]);

  return (
    <div className="h-full bg-white">
      {isLoading && mediaObjects.length === 0 ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 p-6">
          {/* Show skeleton placeholders for initial load */}
          {Array.from({ length: ITEMS_PER_PAGE }).map((_, index) => (
            <div key={`skeleton-${index}`} className="bg-white overflow-hidden shadow-sm">
              <div className="relative aspect-square">
                <Skeleton className="absolute inset-0" />
                {/* Skeleton for description overlay */}
                <div className="absolute bottom-0 left-0 right-0 p-4">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2 mt-2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error && mediaObjects.length === 0 ? (
        <div className="text-center text-red-600 p-8">
          <p>{error}</p>
          <button
            onClick={() => fetchMediaObjects(true)}
            className="mt-4 inline-flex items-center rounded-lg bg-jl-red px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-jl-red-700 transition-colors duration-200"
          >
            Try Again
          </button>
        </div>
      ) : mediaObjects.length === 0 ? (
        <div className="border-2 border-dashed border-gray-300 rounded-xl p-16 text-center mx-8 my-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No media objects
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Media objects will be displayed here once available.
          </p>
          <div className="mt-6">
            <button
              onClick={() => fetchMediaObjects(true)}
              className="inline-flex items-center rounded-lg bg-jl-red px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-jl-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-jl-red transition-colors duration-200"
            >
              <svg
                className="-ml-0.5 mr-1.5 h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-11.25a.75.75 0 00-1.5 0v2.5h-2.5a.75.75 0 000 1.5h2.5v2.5a.75.75 0 001.5 0v-2.5h2.5a.75.75 0 000-1.5h-2.5v-2.5z"
                  clipRule="evenodd"
                />
              </svg>
              Refresh Gallery
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 p-6">
            {mediaObjects.map((media) => (
              <MediaThumbnail key={media.id} media={media} />
            ))}
          </div>

          {/* Loading indicator for infinite scroll */}
          {isLoading && mediaObjects.length > 0 && (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 px-6 pb-6">
              {/* Show 12 skeleton items when loading more */}
              {Array.from({ length: 12 }).map((_, index) => (
                <div key={`skeleton-more-${index}`} className="bg-white overflow-hidden shadow-sm">
                  <div className="relative aspect-square">
                    <Skeleton className="absolute inset-0" />
                    <div className="absolute bottom-0 left-0 right-0 p-4">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-1/2 mt-2" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <div ref={loadingRef} className="py-8">
            {!hasMore && mediaObjects.length > 0 && (
              <p className="text-gray-500 text-sm text-center">
                No more media objects to load
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
