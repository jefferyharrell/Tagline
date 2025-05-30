"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import MediaThumbnail from "@/components/MediaThumbnail";
import MediaModal from "@/components/MediaModal";
import MediaDetailClient from "./[id]/media-detail-client";
import { Skeleton } from "@/components/ui/skeleton";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { MediaObject } from "@/types/media";

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
  const isFetchingRef = useRef(false);
  
  // Modal state
  const [selectedMedia, setSelectedMedia] = useState<MediaObject | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const ITEMS_PER_PAGE = 36;
  
  // Handle opening media in modal
  const handleMediaClick = useCallback(async (media: MediaObject) => {
    // Fetch full media details
    try {
      const response = await fetch(`/api/library/${media.id}`);
      if (response.ok) {
        const fullMedia = await response.json();
        setSelectedMedia(fullMedia);
        setIsModalOpen(true);
        // Update URL without navigation
        window.history.pushState({}, '', `/library/${media.id}`);
      }
    } catch (error) {
      console.error("Error fetching media details:", error);
      // Fall back to using the basic media object
      setSelectedMedia(media);
      setIsModalOpen(true);
      window.history.pushState({}, '', `/library/${media.id}`);
    }
  }, []);
  
  // Handle closing modal
  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedMedia(null);
    // Return to gallery URL
    window.history.pushState({}, '', '/library');
  }, []);
  
  // Handle browser back/forward buttons
  useEffect(() => {
    let isMounted = false;
    
    const handlePopState = async () => {
      const path = window.location.pathname;
      const match = path.match(/\/library\/([a-zA-Z0-9_-]+)$/);
      
      if (match && match[1]) {
        // We're on a detail URL, find and show the media
        const mediaId = match[1];
        
        // Don't fetch on initial mount - the page component will handle that
        if (!isMounted) {
          return;
        }
        
        const media = mediaObjects.find(m => m.id === mediaId);
        if (media) {
          // Fetch full media details
          try {
            const response = await fetch(`/api/library/${mediaId}`);
            if (response.ok) {
              const fullMedia = await response.json();
              setSelectedMedia(fullMedia);
              setIsModalOpen(true);
            }
          } catch (error) {
            console.error("Error fetching media details:", error);
            setSelectedMedia(media);
            setIsModalOpen(true);
          }
        } else {
          // Media not in current list, try to fetch it anyway
          try {
            const response = await fetch(`/api/library/${mediaId}`);
            if (response.ok) {
              const fullMedia = await response.json();
              setSelectedMedia(fullMedia);
              setIsModalOpen(true);
            } else {
              // Can't load media, close modal
              setIsModalOpen(false);
              setSelectedMedia(null);
            }
          } catch (error) {
            console.error("Error fetching media details:", error);
            setIsModalOpen(false);
            setSelectedMedia(null);
          }
        }
      } else if (path === '/library' || path === '/library/') {
        // We're on the gallery URL, close modal
        setIsModalOpen(false);
        setSelectedMedia(null);
      }
    };
    
    window.addEventListener('popstate', handlePopState);
    
    // Small delay before checking initial URL to ensure component is ready
    setTimeout(() => {
      isMounted = true;
      handlePopState();
    }, 100);
    
    return () => window.removeEventListener('popstate', handlePopState);
  }, [mediaObjects]);

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
      } catch (err) {
        console.error("Error fetching media objects:", err);
        setError((err as Error).message || "Failed to fetch media objects");
      } finally {
        isFetchingRef.current = false;
        setIsLoading(false);
      }
    },
    [offset, isLoading, hasMore, searchQuery],
  );

  const [hasInitialized, setHasInitialized] = useState(false);

  // Initialize data load
  useEffect(() => {
    if (!hasInitialized) {
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
      isFetchingRef.current = false;
      fetchMediaObjects(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

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
      {/* Header with Sidebar Trigger and Search Bar */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-4">
          {/* Sidebar Trigger */}
          <SidebarTrigger />
          
          {/* Search Bar */}
          <div className="flex-1 max-w-2xl">
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
              <MediaThumbnail key={media.id} media={media} onClick={handleMediaClick} />
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
      
      {/* Modal for media detail */}
      <MediaModal isOpen={isModalOpen} onClose={handleCloseModal}>
        {selectedMedia && (
          <MediaDetailClient 
            initialMediaObject={selectedMedia} 
            isModal={true}
            onClose={handleCloseModal}
          />
        )}
      </MediaModal>
    </div>
  );
}
