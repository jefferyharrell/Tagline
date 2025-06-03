"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Folder, Home } from "lucide-react";
import { useRouter } from "next/navigation";
import MediaThumbnail from "@/components/MediaThumbnail";
import MediaModal from "@/components/MediaModal";
import MediaDetailClient from "../../[object_key]/media-detail-client";
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
import { useIngestEvents } from "@/hooks/use-ingest-events";

interface DirectoryItem {
  name: string;
  is_folder: boolean;
  object_key?: string;
  size?: number;
  last_modified?: string;
  mimetype?: string;
}

interface BrowseResponse {
  folders: DirectoryItem[];
  media_objects: MediaObject[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

interface BrowseClientProps {
  initialPath: string;
}

export default function BrowseClient({ initialPath }: BrowseClientProps) {
  const router = useRouter();
  const [currentPath, setCurrentPath] = useState<string[]>(() => 
    initialPath ? initialPath.split('/').filter(Boolean).map(segment => decodeURIComponent(segment)) : []
  );
  const [folders, setFolders] = useState<DirectoryItem[]>([]);
  const [mediaObjects, setMediaObjects] = useState<MediaObject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [, ] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [ingestStatus, setIngestStatus] = useState<string>("");
  const [, setIngestedObjects] = useState<Set<string>>(new Set());
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [pendingMediaObjects, setPendingMediaObjects] = useState<MediaObject[]>([]);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadingRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isFetchingRef = useRef(false);

  // Modal state
  const [selectedMedia, setSelectedMedia] = useState<MediaObject | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const ITEMS_PER_PAGE = 36;


  // Handle real-time ingest updates
  const handleMediaIngested = useCallback((objectKey: string) => {
    console.log('Media ingested:', objectKey);
    
    // Add to ingested objects set
    setIngestedObjects(prev => new Set(prev).add(objectKey));
    
    
    // Remove from pending media objects if present
    setPendingMediaObjects(prev => prev.filter(obj => obj.object_key !== objectKey));
    
    // Check if this object is in the current path context
    const pathString = currentPath.length > 0 ? currentPath.join('/') : '';
    const expectedPrefix = pathString ? `/${pathString}/` : '/';
    
    if (objectKey.startsWith(expectedPrefix)) {
      // This object belongs to the current folder, trigger a refresh
      setRefreshTrigger(prev => prev + 1);
      
      // Show success notification
      setIngestStatus(`New photo processed: ${objectKey.split('/').pop()}`);
      setTimeout(() => setIngestStatus(""), 3000);
    }
  }, [currentPath]);

  const handleSSEError = useCallback((error: string) => {
    console.error('SSE Error:', error);
    setIngestStatus(`Connection error: ${error}`);
    setTimeout(() => setIngestStatus(""), 5000);
  }, []);

  // Initialize SSE connection
  const { isConnected } = useIngestEvents({
    onMediaIngested: handleMediaIngested,
    onError: handleSSEError,
    enabled: true,
  });

  // Navigate to a folder
  const navigateToFolder = (folderName: string) => {
    const newPath = [...currentPath, folderName];
    setCurrentPath(newPath);
    const newPathString = newPath.map(segment => encodeURIComponent(segment)).join('/');
    router.push(`/library/browse/${newPathString}`);
    setOffset(0);
    setHasMore(true);
  };

  // Navigate to a breadcrumb
  const navigateToBreadcrumb = (index: number) => {
    const newPath = currentPath.slice(0, index + 1);
    setCurrentPath(newPath);
    const newPathString = newPath.map(segment => encodeURIComponent(segment)).join('/');
    router.push(`/library/browse/${newPathString}`);
    setOffset(0);
    setHasMore(true);
  };

  // Navigate to root
  const navigateToRoot = () => {
    // Only navigate if we're not already at root
    if (currentPath.length > 0) {
      setCurrentPath([]);
      router.push('/library/browse');
      setOffset(0);
      setHasMore(true);
    }
  };

  // Get icon for file type (reserved for future use)
  // const getFileIcon = (mimetype?: string) => {
  //   if (!mimetype) return <File className="w-5 h-5 text-gray-400" alt="" />;
  //   
  //   if (mimetype.startsWith('image/')) {
  //     return <Image className="w-5 h-5 text-blue-500" alt="" />;
  //   }
  //   if (mimetype.startsWith('video/')) {
  //     return <Video className="w-5 h-5 text-purple-500" alt="" />;
  //   }
  //   return <FileText className="w-5 h-5 text-gray-400" alt="" />;
  // };

  // Handle opening media in modal
  const handleMediaClick = useCallback(async (media: MediaObject) => {
    try {
      const response = await fetch(`/api/library/${media.object_key}`);
      if (response.ok) {
        const fullMedia = await response.json();
        setSelectedMedia(fullMedia);
        setIsModalOpen(true);
        window.history.pushState({}, "", `/library/${media.object_key}`);
      }
    } catch (error) {
      console.error("Error fetching media details:", error);
      setSelectedMedia(media);
      setIsModalOpen(true);
      window.history.pushState({}, "", `/library/${media.object_key}`);
    }
  }, []);

  // Handle closing modal
  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedMedia(null);
    const encodedPath = currentPath.map(segment => encodeURIComponent(segment)).join('/');
    const url = encodedPath ? `/library/browse/${encodedPath}` : '/library/browse';
    window.history.pushState({}, "", url);
  }, [currentPath]);

  // Fetch browse data (folders and media objects) - unified API call
  const fetchBrowseData = useCallback(async (reset: boolean = false) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    try {
      const pathString = currentPath.length > 0 ? currentPath.join('/') : '';
      const currentOffset = reset ? 0 : offset;
      
      // Build URL with search or path-based filtering
      const url = searchQuery && searchQuery.trim() !== ""
        ? `/api/library/search?q=${encodeURIComponent(searchQuery)}&limit=${ITEMS_PER_PAGE}&offset=${currentOffset}`
        : pathString 
          ? `/api/storage/browse?path=${encodeURIComponent(pathString)}&limit=${ITEMS_PER_PAGE}&offset=${currentOffset}`
          : `/api/storage/browse?limit=${ITEMS_PER_PAGE}&offset=${currentOffset}`;

      const response = await fetch(url);
      if (response.ok) {
        if (searchQuery && searchQuery.trim() !== "") {
          // Handle search response (different structure)
          const data: { items: MediaObject[]; total: number; limit: number; offset: number } = await response.json();
          const sanitizedItems = data.items.map((item) => ({
            ...item,
            metadata: item.metadata || {},
          }));
          
          if (reset) {
            setFolders([]); // No folders in search results
            setMediaObjects(sanitizedItems);
            setOffset(data.items.length);
          } else {
            setMediaObjects((prev) => {
              const existingIds = new Set(prev.map((item) => item.object_key));
              const newItems = sanitizedItems.filter(
                (item) => !existingIds.has(item.object_key),
              );
              return [...prev, ...newItems];
            });
            setOffset(currentOffset + data.items.length);
          }
          
          setHasMore(currentOffset + data.items.length < data.total);
          setPendingMediaObjects([]);
        } else {
          // Handle browse response
          const data: BrowseResponse = await response.json();
          const sanitizedItems = data.media_objects.map((item) => ({
            ...item,
            metadata: item.metadata || {},
          }));
          
          if (reset) {
            setFolders(data.folders);
            setMediaObjects(sanitizedItems);
            setOffset(data.media_objects.length);
          } else {
            setMediaObjects((prev) => {
              const existingIds = new Set(prev.map((item) => item.object_key));
              const newItems = sanitizedItems.filter(
                (item) => !existingIds.has(item.object_key),
              );
              return [...prev, ...newItems];
            });
            setOffset(currentOffset + data.media_objects.length);
          }
          
          setHasMore(data.has_more);
          
          // Identify pending media objects (those without thumbnails)
          const pending = sanitizedItems.filter(obj => 
            obj.ingestion_status === 'pending' || !obj.has_thumbnail
          );
          setPendingMediaObjects(pending);
          
          
          if (pending.length > 0) {
            setIngestStatus(`${pending.length} files queued for processing...`);
            setTimeout(() => setIngestStatus(""), 5000);
          }
        }
        
        setInitialLoad(false);
      }
    } catch (err) {
      console.error("Error fetching browse data:", err);
      setFolders([]);
      setMediaObjects([]);
    } finally {
      isFetchingRef.current = false;
      setIsLoading(false);
      setIsTransitioning(false);
    }
  }, [currentPath, searchQuery, offset]);

  // Unified fetch function that gets both folders and media objects
  const fetchData = useCallback(
    async (reset: boolean = false) => {
      if ((!hasMore && !reset) || isFetchingRef.current) return;

      if (reset && mediaObjects.length > 0) {
        setIsTransitioning(true);
      } else {
        setIsLoading(true);
      }

      await fetchBrowseData(reset);
    },
    [fetchBrowseData, hasMore, mediaObjects.length],
  );

  const [hasInitialized, setHasInitialized] = useState(false);

  // Initialize data load
  useEffect(() => {
    if (!hasInitialized) {
      fetchData(true);
      setHasInitialized(true);
    }
  }, [hasInitialized, fetchData]);

  // Reload when path changes
  useEffect(() => {
    if (hasInitialized) {
      fetchData(true);
    }
  }, [currentPath, hasInitialized, fetchData]);

  // Reload when search query changes
  useEffect(() => {
    if (hasInitialized) {
      fetchData(true);
    }
  }, [searchQuery, hasInitialized, fetchData]);

  // Handle refresh trigger from SSE events
  useEffect(() => {
    if (hasInitialized && refreshTrigger > 0) {
      fetchData(true);
    }
  }, [refreshTrigger, hasInitialized, fetchData]);

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
            fetchData();
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
  }, [fetchData, hasMore, isLoading, initialLoad, mediaObjects.length]);

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

        {/* Ingest Status and Connection Status */}
        <div className="mt-2 flex items-center justify-between">
          {ingestStatus && (
            <div className="text-sm text-blue-600">
              {ingestStatus}
            </div>
          )}
          
          {/* SSE Connection Status */}
          <div className="flex items-center text-xs text-gray-500">
            <div 
              className={`w-2 h-2 rounded-full mr-1 ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            {isConnected ? 'Live updates active' : 'Live updates disconnected'}
          </div>
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
                          {decodeURIComponent(segment)}
                        </BreadcrumbPage>
                      ) : (
                        <BreadcrumbLink
                          asChild
                          className="text-jl-red hover:text-jl-red-700 cursor-pointer"
                        >
                          <button onClick={() => navigateToBreadcrumb(index)}>
                            {decodeURIComponent(segment)}
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
          {folders.length > 0 && (
            <div className="divide-y divide-gray-200 border-t border-gray-200">
              {folders.map((folder) => (
                <button
                  key={folder.name}
                  onClick={() => navigateToFolder(folder.name)}
                  className="w-full flex items-center px-6 py-3 hover:bg-gray-50 transition-colors text-left"
                >
                  <Folder className="w-5 h-5 text-jl-red mr-3" />
                  <span className="text-sm">{folder.name}</span>
                </button>
              ))}
            </div>
          )}

          {/* No subfolders message */}
          {folders.length === 0 && !isLoading && (
            <div className="px-6 py-4 text-center text-gray-500 text-sm">
              No subfolders in this directory
            </div>
          )}
        </div>

        {/* Media Gallery */}
        {mediaObjects.length === 0 && pendingMediaObjects.length === 0 && !isLoading && !isTransitioning ? (
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
        ) : isLoading && mediaObjects.length === 0 && pendingMediaObjects.length === 0 && folders.length === 0 ? (
          // Show minimal loading state only on true initial load
          <div className="flex items-center justify-center py-16">
            <div className="inline-flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-gray-600">Loading...</span>
            </div>
          </div>
        ) : (
          <>
            <div
              className={`grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 ${isTransitioning ? "opacity-50" : ""} transition-opacity duration-200`}
            >
              {/* Render media objects - both completed and pending */}
              {mediaObjects.map((media) => {
                // Check if this media object is pending (no thumbnail)
                const isPending = media.ingestion_status === 'pending' || !media.has_thumbnail;
                
                if (isPending) {
                  // Show skeleton for pending media objects
                  return (
                    <div
                      key={`pending-${media.object_key}`}
                      className="bg-white overflow-hidden shadow-sm rounded-lg relative"
                    >
                      <div className="relative aspect-square">
                        <Skeleton className="absolute inset-0" />
                        {/* Processing indicator */}
                        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20">
                          <div className="text-white text-xs bg-black bg-opacity-50 px-2 py-1 rounded">
                            Processing...
                          </div>
                        </div>
                      </div>
                      <div className="p-3">
                        <div className="text-sm text-gray-600 truncate">
                          {media.object_key?.split('/').pop() || 'Unknown file'}
                        </div>
                      </div>
                    </div>
                  );
                }
                
                // Show regular thumbnail for completed media objects
                return (
                  <MediaThumbnail
                    key={media.object_key}
                    media={media}
                    onClick={handleMediaClick}
                  />
                );
              })}
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