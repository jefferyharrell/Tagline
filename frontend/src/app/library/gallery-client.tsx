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
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadingRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isRestoringScroll, setIsRestoringScroll] = useState(false);
  const hasRestoredScrollRef = useRef(false);
  const isFetchingRef = useRef(false);

  const ITEMS_PER_PAGE = 36;

  const fetchMediaObjects = useCallback(
    async (reset: boolean = false) => {
      if (isLoading || (!hasMore && !reset) || isFetchingRef.current) return;

      const currentOffset = reset ? 0 : offset;
      isFetchingRef.current = true;
      setIsLoading(true);
      setError(null);

      try {
        const url = searchQuery && searchQuery.trim() !== ""
          ? `/api/library/search?q=${encodeURIComponent(searchQuery)}&limit=${ITEMS_PER_PAGE}&offset=${currentOffset}`
          : `/api/library?limit=${ITEMS_PER_PAGE}&offset=${currentOffset}`;
        
        const response = await fetch(url);

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
          setMediaObjects((prev) => {
            // Create a Set of existing IDs to prevent duplicates
            const existingIds = new Set(prev.map(item => item.id));
            const newItems = sanitizedItems.filter(item => !existingIds.has(item.id));
            return [...prev, ...newItems];
          });
        }

        // Check if we've loaded all items
        setHasMore(currentOffset + data.items.length < data.total);
        const newOffset = currentOffset + data.items.length;
        setOffset(newOffset);
        setInitialLoad(false);
        
        // Store current offset in sessionStorage for scroll restoration
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('library-current-offset', newOffset.toString());
        }
      } catch (err) {
        console.error("Error fetching media objects:", err);
        setError((err as Error).message || "Failed to fetch media objects");
      } finally {
        isFetchingRef.current = false;
        setIsLoading(false);
      }
    },
    [offset, isLoading, hasMore, searchQuery, searchInput],
  );

  const [hasInitialized, setHasInitialized] = useState(false);

  // Restore scroll position after content loads
  const restoreScrollPosition = useCallback(() => {
    if (hasRestoredScrollRef.current) return;
    
    const savedPosition = sessionStorage.getItem('library-scroll-position');
    const savedOffset = sessionStorage.getItem('library-saved-offset');
    
    
    if (savedPosition && savedOffset) {
      const targetPosition = parseInt(savedPosition, 10);
      const targetOffset = parseInt(savedOffset, 10);
      
      // Check if we have loaded enough content
      if (offset >= targetOffset) {
        // Content is loaded, restore scroll position
        hasRestoredScrollRef.current = true;
        // Add a small delay to ensure DOM is fully ready
        setTimeout(() => {
          // Try multiple methods to ensure scroll works
          window.scrollTo(0, targetPosition);
          document.documentElement.scrollTop = targetPosition;
          document.body.scrollTop = targetPosition;
          
          // Double-check the scroll worked
          requestAnimationFrame(() => {
            const currentScroll = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
            
            if (Math.abs(currentScroll - targetPosition) > 10) {
              window.scrollTo({ top: targetPosition, behavior: 'instant' });
            }
            
            // Clean up after successful restoration
            sessionStorage.removeItem('library-scroll-position');
            sessionStorage.removeItem('library-saved-offset');
            setIsRestoringScroll(false);
          });
        }, 100);
      } else if (hasMore && !isLoading) {
        // Need to load more content
        setIsRestoringScroll(true);
        fetchMediaObjects();
      }
    } else {
      // No saved position, we're done
      setIsRestoringScroll(false);
    }
  }, [offset, hasMore, isLoading, fetchMediaObjects]);

  // Initialize data load
  useEffect(() => {
    if (!hasInitialized) {
      // Disable browser scroll restoration
      if ('scrollRestoration' in history) {
        history.scrollRestoration = 'manual';
      }
      
      // Check if we're returning from detail view
      const savedPosition = sessionStorage.getItem('library-scroll-position');
      const savedOffset = sessionStorage.getItem('library-saved-offset');
      
      
      if (savedPosition && savedOffset) {
        // We're returning - start restoration process
        setIsRestoringScroll(true);
      }
      
      fetchMediaObjects(true);
      setHasInitialized(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle search query changes
  useEffect(() => {
    if (hasInitialized) {
      setOffset(0);
      setHasMore(true);
      hasRestoredScrollRef.current = false;
      setIsRestoringScroll(false);
      isFetchingRef.current = false;
      // Clear saved scroll position when search changes
      sessionStorage.removeItem('library-scroll-position');
      sessionStorage.removeItem('library-saved-offset');
      fetchMediaObjects(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);
  
  // Try to restore scroll position after content loads
  useEffect(() => {
    if (isRestoringScroll && !isLoading) {
      restoreScrollPosition();
    }
  }, [isRestoringScroll, isLoading, offset, restoreScrollPosition]);

  // Setup intersection observer for infinite scroll
  useEffect(() => {
    if (loadingRef.current && !initialLoad) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          const [entry] = entries;
          if (entry.isIntersecting && hasMore && !isLoading && !isRestoringScroll) {
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
  }, [fetchMediaObjects, hasMore, isLoading, initialLoad, isRestoringScroll]);

  // Handle search input with debounce
  const handleSearchInput = (value: string) => {
    setSearchInput(value);
    
    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    // Set new timeout for debounced search
    searchTimeoutRef.current = setTimeout(() => {
      setSearchQuery(value);
    }, 300);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="h-full bg-white">
      {/* Search Bar */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-2xl mx-auto">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-jl-red focus:border-transparent"
              placeholder="Search photos by keyword..."
              value={searchInput}
              onChange={(e) => handleSearchInput(e.target.value)}
            />
            {searchInput && (
              <button
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => {
                  setSearchInput("");
                  setSearchQuery("");
                }}
              >
                <svg
                  className="h-5 w-5 text-gray-400 hover:text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
          {searchQuery !== "" && (
            <p className="mt-2 text-sm text-gray-600">
              Searching for: <span className="font-medium">{searchQuery}</span>
            </p>
          )}
        </div>
      </div>
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
            {searchQuery ? "No results found" : "No media objects"}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchQuery 
              ? `No photos match your search for "${searchQuery}"`
              : "Media objects will be displayed here once available."}
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
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 p-6 mt-2">
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
