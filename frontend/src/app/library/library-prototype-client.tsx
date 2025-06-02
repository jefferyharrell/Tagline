"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Folder, Home } from "lucide-react";
import MediaThumbnail from "@/components/MediaThumbnail";
import MediaModal from "@/components/MediaModal";
import MediaDetailClient from "./[object_key]/media-detail-client";
import { Skeleton } from "@/components/ui/skeleton";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { MediaObject } from "@/types/media";

interface PaginatedResponse {
  items: MediaObject[];
  total: number;
  limit: number;
  offset: number;
}

// Mock folder structure - same as IngestClient
const mockFolderStructure = {
  "2024": {
    "Spring Gala": {
      Photos: {
        Arrivals: {},
        "Cocktail Hour": {},
        Dinner: {},
        Speeches: {},
        Dancing: {},
        "Group Photos": {},
        Candids: {},
        "Venue Shots": {},
        Decorations: {},
        "Behind the Scenes": {},
      },
      Videos: {
        "Highlights Reel": {},
        "Full Speeches": {},
        "Dance Floor": {},
        Interviews: {},
        "B-Roll": {},
      },
    },
    "Volunteer Fair": {
      Setup: {},
      Event: {},
      Cleanup: {},
    },
    "Annual Fundraiser": {},
    "Board Meetings": {},
    "Community Outreach": {},
    "Member Events": {},
    "Marketing Materials": {},
    "Press Coverage": {},
    "Social Media Content": {},
  },
  "2023": {
    "Holiday Party": {},
    "Summer Picnic": {},
    "Fall Fashion Show": {},
    "Winter Ball": {},
    "Spring Luncheon": {},
    "Charity Auction": {},
    "Golf Tournament": {},
    "5K Run": {},
    "Book Club Events": {},
    "Wine Tasting": {},
    "Art Exhibition": {},
    "Cooking Classes": {},
    "Mentorship Program": {},
    "Professional Development": {},
    "Volunteer Recognition": {},
  },
  "2022": {},
  "2021": {},
  "2020": {},
  Archives: {},
  Administrative: {},
  "Special Projects": {},
};

export default function LibraryPrototypeClient() {
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [mediaObjects, setMediaObjects] = useState<MediaObject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [, setError] = useState<string | null>(null);
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

  // Navigate through the folder structure based on current path
  const getCurrentFolder = () => {
    let current: Record<string, unknown> = mockFolderStructure;
    for (const segment of currentPath) {
      current = (current[segment] as Record<string, unknown>) || {};
    }
    return current;
  };

  // Get the subfolders in the current directory
  const getSubfolders = () => {
    const current = getCurrentFolder();
    return Object.keys(current).filter(
      (key) => typeof current[key] === "object" && current[key] !== null,
    );
  };

  // Handle clicking into a subfolder
  const navigateToFolder = (folderName: string) => {
    setCurrentPath([...currentPath, folderName]);
    // Don't clear media immediately - let fetchMediaObjects handle it
    setOffset(0);
    setHasMore(true);
  };

  // Handle clicking on a breadcrumb to navigate back
  const navigateToBreadcrumb = (index: number) => {
    setCurrentPath(currentPath.slice(0, index + 1));
    // Don't clear media immediately - let fetchMediaObjects handle it
    setOffset(0);
    setHasMore(true);
  };

  // Go back to root
  const navigateToRoot = () => {
    setCurrentPath([]);
    // Don't clear media immediately - let fetchMediaObjects handle it
    setOffset(0);
    setHasMore(true);
  };

  // Generate the object prefix from current path
  // Keeping for future use when we implement path-based filtering
  // const generatePrefix = () => {
  //   return currentPath.join("/") + (currentPath.length > 0 ? "/" : "");
  // };

  // Handle opening media in modal
  const handleMediaClick = useCallback(async (media: MediaObject) => {
    try {
      const response = await fetch(`/api/library/${encodeURIComponent(media.object_key)}`);
      if (response.ok) {
        const fullMedia = await response.json();
        setSelectedMedia(fullMedia);
        setIsModalOpen(true);
        window.history.pushState({}, "", `/library/${encodeURIComponent(media.object_key)}`);
      }
    } catch (error) {
      console.error("Error fetching media details:", error);
      setSelectedMedia(media);
      setIsModalOpen(true);
      window.history.pushState({}, "", `/library/${encodeURIComponent(media.object_key)}`);
    }
  }, []);

  // Handle closing modal
  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedMedia(null);
    window.history.pushState({}, "", "/library");
  }, []);

  const fetchMediaObjects = useCallback(
    async (reset: boolean = false) => {
      if (isLoading || (!hasMore && !reset) || isFetchingRef.current) return;

      const currentOffset = reset ? 0 : offset;
      isFetchingRef.current = true;

      // Only show loading for initial load or when appending more items
      if (reset && mediaObjects.length > 0) {
        setIsTransitioning(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        // In a real implementation, we would filter by the current path
        // const prefix = generatePrefix(); // Keeping for future use
        const url =
          searchQuery && searchQuery.trim() !== ""
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
            const existingKeys = new Set(prev.map((item) => item.object_key));
            const newItems = sanitizedItems.filter(
              (item) => !existingKeys.has(item.object_key),
            );
            return [...prev, ...newItems];
          });
        }

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
        setIsTransitioning(false);
      }
    },
    [offset, isLoading, hasMore, searchQuery, mediaObjects.length],
  );

  const [hasInitialized, setHasInitialized] = useState(false);

  // Initialize data load
  useEffect(() => {
    if (!hasInitialized) {
      fetchMediaObjects(true);
      setHasInitialized(true);
    }
  }, [hasInitialized, fetchMediaObjects]);

  // Reload when path changes
  useEffect(() => {
    if (hasInitialized) {
      fetchMediaObjects(true);
    }
  }, [currentPath, hasInitialized, fetchMediaObjects]);

  // Handle search input with debounce
  const handleSearchInput = (value: string) => {
    setSearchInput(value);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      setSearchQuery(value);
    }, 300);
  };

  // Setup intersection observer for infinite scroll
  useEffect(() => {
    if (loadingRef.current && !initialLoad && mediaObjects.length > 0) {
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
  }, [fetchMediaObjects, hasMore, isLoading, initialLoad, mediaObjects.length]);

  const subfolders = getSubfolders();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with Sidebar Trigger and Search Bar */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center">
          {/* Left: Sidebar Trigger */}
          <div className="flex-1">
            <SidebarTrigger />
          </div>

          {/* Center: Search Bar */}
          <div className="flex-[3] flex justify-center">
            <div className="w-full max-w-2xl">
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
            </div>
          </div>

          {/* Right: Reserved space */}
          <div className="flex-1">{/* Reserved for future use */}</div>
        </div>
      </div>

      <div className="container mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Navigation Card */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden mb-8">
          {/* Breadcrumb Navigation */}
          <div className="px-6 py-4 border-b border-gray-200">
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink
                    asChild
                    className="flex items-center text-jl-red hover:text-jl-red-700 cursor-pointer"
                  >
                    <button onClick={navigateToRoot}>
                      <Home className="w-4 h-4 mr-1" />
                      Home
                    </button>
                  </BreadcrumbLink>
                </BreadcrumbItem>

                {currentPath.map((segment, index) => (
                  <React.Fragment key={index}>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      {index === currentPath.length - 1 ? (
                        <BreadcrumbPage className="text-gray-900">
                          {segment}
                        </BreadcrumbPage>
                      ) : (
                        <BreadcrumbLink
                          asChild
                          className="text-jl-red hover:text-jl-red-700 cursor-pointer"
                        >
                          <button onClick={() => navigateToBreadcrumb(index)}>
                            {segment}
                          </button>
                        </BreadcrumbLink>
                      )}
                    </BreadcrumbItem>
                  </React.Fragment>
                ))}
              </BreadcrumbList>
            </Breadcrumb>
          </div>

          {/* Folder List */}
          {subfolders.length > 0 && (
            <div className="divide-y divide-gray-200 border-t border-gray-200">
              {subfolders.slice(0, 5).map((folder) => (
                <button
                  key={folder}
                  onClick={() => navigateToFolder(folder)}
                  className="w-full flex items-center px-6 py-3 hover:bg-gray-50 transition-colors text-left"
                >
                  <Folder className="w-5 h-5 text-jl-red mr-3" />
                  <span className="text-sm">{folder}</span>
                </button>
              ))}
            </div>
          )}

          {/* No subfolders message */}
          {subfolders.length === 0 && (
            <div className="px-6 py-4 text-center text-gray-500 text-sm">
              No subfolders in this directory
            </div>
          )}
        </div>

        {/* Media Gallery */}
        {mediaObjects.length === 0 && !isLoading && !isTransitioning ? (
          <div className="border-2 border-dashed border-gray-300 rounded-xl p-16 text-center">
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
              No photos in this folder
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Navigate to a folder with photos or try searching
            </p>
          </div>
        ) : isLoading && mediaObjects.length === 0 ? (
          // Show skeletons only on initial load
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
            {Array.from({ length: 12 }).map((_, index) => (
              <div
                key={`skeleton-${index}`}
                className="bg-white overflow-hidden shadow-sm rounded-lg"
              >
                <div className="relative aspect-square">
                  <Skeleton className="absolute inset-0" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
            <div
              className={`grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 ${isTransitioning ? "opacity-50" : ""} transition-opacity duration-200`}
            >
              {mediaObjects.map((media) => (
                <MediaThumbnail
                  key={media.object_key}
                  media={media}
                  onClick={handleMediaClick}
                />
              ))}
            </div>

            {/* Loading indicator for infinite scroll */}
            {isLoading && mediaObjects.length > 0 && !isTransitioning && (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 mt-6">
                {Array.from({ length: 12 }).map((_, index) => (
                  <div
                    key={`skeleton-more-${index}`}
                    className="bg-white overflow-hidden shadow-sm rounded-lg"
                  >
                    <div className="relative aspect-square">
                      <Skeleton className="absolute inset-0" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div ref={loadingRef} className="py-8">
              {!hasMore && mediaObjects.length > 0 && (
                <p className="text-gray-500 text-sm text-center">
                  No more photos to load
                </p>
              )}
            </div>
          </>
        )}
      </div>

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
