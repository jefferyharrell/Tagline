'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Home, AlertCircle, RefreshCw } from 'lucide-react';
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb';
import { Button } from '@/components/ui/button';
import MobilePageHeader from './MobilePageHeader';
import FolderList from './FolderList';
import ThumbnailGrid from './ThumbnailGrid';
import PhotoThumbnail from './PhotoThumbnail';
import MediaModal from './MediaModal';
import { useSSE, type IngestEvent } from '@/contexts/sse-context';
import type { MediaObject } from '@/types/media';
import logger from '@/lib/logger';

interface LibraryViewProps {
  initialPath: string;
  className?: string;
}

interface FolderItem {
  name: string;
  is_folder: boolean;
}

interface BrowseResponse {
  folders: FolderItem[];
  media_objects: MediaObject[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export default function LibraryView({ initialPath, className = '' }: LibraryViewProps) {
  const router = useRouter();
  
  // Parse initial path into array
  const parsedInitialPath = initialPath ? initialPath.split('/').filter(Boolean) : [];
  
  // State management
  const [currentPath, setCurrentPath] = useState<string[]>(parsedInitialPath);
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [photos, setPhotos] = useState<MediaObject[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number>(-1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [showLoadingSpinner, setShowLoadingSpinner] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Infinite scrolling state
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const offsetRef = useRef(0);
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Fetch data from API
  const fetchData = useCallback(async (path: string[], isLoadMore = false, forceRefresh = false) => {
    if (isLoadMore) {
      setIsLoadingMore(true);
    } else {
      setError(null);
      setIsInitialLoading(true);
      setShowLoadingSpinner(false);
      offsetRef.current = 0;
      
      // Set up a timeout to show loading spinner after 500ms
      loadingTimeoutRef.current = setTimeout(() => {
        setShowLoadingSpinner(true);
      }, 500);
    }
    
    try {
      const pathString = path.join('/');
      const currentOffset = isLoadMore ? offsetRef.current : 0;
      const url = new URL('/api/library', window.location.origin);
      url.searchParams.set('path', pathString);
      url.searchParams.set('offset', currentOffset.toString());
      url.searchParams.set('limit', '100');
      if (forceRefresh) {
        url.searchParams.set('refresh', 'true');
        console.log('📡 fetchData with forceRefresh - URL:', url.toString());
      }
      const response = await fetch(url.toString());
      
      if (!response.ok) {
        throw new Error(`Failed to load library: ${response.statusText}`);
      }
      
      const data: BrowseResponse = await response.json();
      
      if (forceRefresh) {
        console.log('📡 Received refresh data - folders:', data.folders?.length, 'photos:', data.media_objects?.length);
        console.log('📡 New folders:', data.folders?.map(f => f.name));
      }
      
      if (isLoadMore) {
        // Append new photos to existing ones, but deduplicate by object_key
        setPhotos(prev => {
          const existingKeys = new Set(prev.map(photo => photo.object_key));
          const newPhotos = (data.media_objects || []).filter(photo => !existingKeys.has(photo.object_key));
          return [...prev, ...newPhotos];
        });
        offsetRef.current += 100;
      } else {
        // Replace photos and folders (initial load or path change)
        if (forceRefresh) {
          console.log('📡 Setting folders state to:', data.folders?.map(f => f.name));
        }
        setFolders(data.folders || []);
        setPhotos(data.media_objects || []);
        offsetRef.current = 100;
      }
      
      setHasMore(data.has_more || false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred loading the library';
      setError(errorMessage);
      
      logger.error(`Failed to fetch library data: ${errorMessage}`, 'LibraryView', {
        path: path.join('/'),
        isLoadMore,
        error: err
      });
    } finally {
      if (isLoadMore) {
        setIsLoadingMore(false);
      } else {
        // Clear the loading timeout if it exists
        if (loadingTimeoutRef.current) {
          clearTimeout(loadingTimeoutRef.current);
          loadingTimeoutRef.current = null;
        }
        setIsInitialLoading(false);
        setShowLoadingSpinner(false);
      }
    }
  }, []);
  
  // Update URL when path changes
  useEffect(() => {
    const pathString = currentPath.join('/');
    const url = pathString ? `/library/${pathString}` : '/library';
    
    logger.debug(`Navigating to library path: ${pathString}`, 'LibraryView', { 
      pathArray: currentPath, 
      url 
    });
    
    router.push(url, { scroll: false });
    fetchData(currentPath);
  }, [currentPath, router, fetchData]);
  
  // Handle folder navigation
  const handleFolderClick = useCallback((folderName: string) => {
    setCurrentPath([...currentPath, folderName]);
  }, [currentPath]);
  
  // Handle breadcrumb navigation
  const handleBreadcrumbClick = useCallback((index: number) => {
    if (index === -1) {
      // Home clicked
      setCurrentPath([]);
    } else {
      setCurrentPath(currentPath.slice(0, index + 1));
    }
  }, [currentPath]);
  
  
  // Handle modal close
  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedPhotoIndex(-1);
  }, []);


  // Handle media update from modal
  const handleMediaUpdate = useCallback((updatedMedia: MediaObject) => {
    // Update the photos array with the updated media object
    setPhotos(prev => 
      prev.map(photo => 
        photo.object_key === updatedMedia.object_key ? updatedMedia : photo
      )
    );
  }, []);

  // Handle ingest events for real-time thumbnail updates
  const handleMediaIngested = useCallback((event: IngestEvent) => {
    logger.info(`Received ingest event for ${event.object_key}`, 'LibraryView', {
      eventType: event.event_type,
      status: event.ingestion_status,
      hasThumbnail: event.has_thumbnail
    });
    
    setPhotos(prev => {
      return prev.map(photo => {
        if (photo.object_key === event.object_key) {
          return { 
            ...photo, 
            has_thumbnail: event.has_thumbnail,
            ingestion_status: event.ingestion_status 
          };
        }
        return photo;
      });
    });
  }, []);

  // Subscribe to SSE events
  const { subscribe } = useSSE();
  
  useEffect(() => {
    // Subscribe to ingest events
    const unsubscribe = subscribe((event: IngestEvent) => {
      // Filter events to only process those relevant to current path
      const decodedPath = currentPath.map(segment => decodeURIComponent(segment));
      const pathPrefix = decodedPath.length > 0 ? decodedPath.join('/') + '/' : '';
      
      // Include event if it's relevant to the current path
      const isRelevant = decodedPath.length === 0 || 
                        event.object_key.startsWith(pathPrefix) ||
                        event.object_key === decodedPath.join('/');
      
      if (isRelevant) {
        handleMediaIngested(event);
      }
    });
    
    return unsubscribe;
  }, [subscribe, currentPath, handleMediaIngested]);
  
  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);
  
  // Load more photos when scrolling near bottom
  const loadMorePhotos = useCallback(() => {
    if (hasMore && !isLoadingMore) {
      fetchData(currentPath, true);
    }
  }, [hasMore, isLoadingMore, currentPath, fetchData]);
  
  // Scroll detection for infinite scrolling
  useEffect(() => {
    const handleScroll = () => {
      if (window.innerHeight + document.documentElement.scrollTop >= 
          document.documentElement.offsetHeight - 1000) { // Load when 1000px from bottom
        loadMorePhotos();
      }
    };
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [loadMorePhotos]);
  
  // Retry failed load
  const handleRetry = useCallback(() => {
    fetchData(currentPath);
  }, [currentPath, fetchData]);
  
  // Handle refresh button click
  const handleRefresh = useCallback(async () => {
    if (isRefreshing) return;
    
    console.log('🔄 Refresh button clicked, currentPath:', currentPath);
    setIsRefreshing(true);
    try {
      const pathString = currentPath.join('/');
      console.log('🔄 Starting refresh for path:', pathString);
      
      // First, clear cache and reload from storage provider
      console.log('🔄 Calling fetchData with forceRefresh=true');
      await fetchData(currentPath, false, true);
      console.log('🔄 fetchData completed');
      
      // Then trigger re-ingest for new content with metadata preservation
      console.log('🔄 Triggering ingest...');
      const response = await fetch('/api/library/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: pathString }),
      });
      
      console.log('🔄 Ingest response status:', response.status);
      if (!response.ok) {
        const errorText = await response.text();
        console.warn('🔄 Ingest trigger failed:', response.statusText, errorText);
        logger.warn(`Ingest trigger failed: ${response.statusText}`, 'LibraryView', {
          path: pathString
        });
        // Don't throw - cache refresh is the important part
      } else {
        const result = await response.json();
        console.log('🔄 Ingest result:', result);
      }
      
      console.log('🔄 Folder refresh completed successfully');
      logger.info('Folder refresh completed', 'LibraryView', {
        path: pathString
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refresh folder';
      console.error('🔄 Refresh failed:', err);
      logger.error(`Refresh failed: ${errorMessage}`, 'LibraryView', {
        path: currentPath.join('/'),
        error: err
      });
      // TODO: Show error toast
    } finally {
      console.log('🔄 Setting isRefreshing to false');
      setIsRefreshing(false);
    }
  }, [currentPath, fetchData, isRefreshing]);
  
  // Render breadcrumb navigation
  const renderBreadcrumbs = () => (
    <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            {currentPath.length === 0 ? (
              // Current page is Home - show as non-clickable
              <BreadcrumbPage className="flex items-center gap-2">
                <Home className="w-4 h-4" />
                <span>Home</span>
              </BreadcrumbPage>
            ) : (
              // Not on Home - show as clickable
              <BreadcrumbLink asChild>
                <button
                  onClick={() => handleBreadcrumbClick(-1)}
                  className="flex items-center gap-2"
                  aria-label="Go to library home"
                >
                  <Home className="w-4 h-4" />
                  <span>Home</span>
                </button>
              </BreadcrumbLink>
            )}
          </BreadcrumbItem>
        
        {currentPath.map((segment, index) => (
          <React.Fragment key={index}>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              {index === currentPath.length - 1 ? (
                // Current page - show as non-clickable
                <BreadcrumbPage>
                  {decodeURIComponent(segment)}
                </BreadcrumbPage>
              ) : (
                // Not current page - show as clickable
                <BreadcrumbLink asChild>
                  <button onClick={() => handleBreadcrumbClick(index)}>
                    {decodeURIComponent(segment)}
                  </button>
                </BreadcrumbLink>
              )}
            </BreadcrumbItem>
          </React.Fragment>
        ))}
        </BreadcrumbList>
      </Breadcrumb>
  );
  
  // Render error state
  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center min-h-[400px] ${className}`}>
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Library</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={handleRetry}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }
  
  return (
    <div className={`${className}`}>
      {/* Mobile Header */}
      <MobilePageHeader title="Library" />
      
      {/* Breadcrumb Navigation */}
      <div className="sticky top-0 z-10 px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          {renderBreadcrumbs()}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="ml-4 shrink-0"
            aria-label="Refresh folder"
            title="Refresh folder"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>
      
      {/* Content Area */}
      <div className="p-6 bg-white">
        {isInitialLoading ? (
          showLoadingSpinner ? (
            /* Initial Loading State - only show after delay */
            <div className="flex justify-center py-16">
              <div className="flex items-center gap-2 text-gray-600">
                <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
                <span>Loading...</span>
              </div>
            </div>
          ) : (
            /* Loading but not showing spinner yet - show nothing */
            <div className="py-16"></div>
          )
        ) : (
          <>
            {/* Folder List */}
            {folders.length > 0 && (
              <>
                <FolderList
                  folders={folders}
                  onFolderClick={handleFolderClick}
                />
                {photos.length > 0 && (
                  <div className="my-6 border-t border-gray-200"></div>
                )}
              </>
            )}
            
            {/* Photo Grid - always render when no folders to show empty state */}
            {(photos.length > 0 || folders.length === 0) && (
              <ThumbnailGrid emptyMessage="No photos in this folder">
            {photos.map((photo, index) => (
              <div key={photo.object_key} className="relative aspect-square overflow-visible">
                <PhotoThumbnail
                  media={photo}
                  position={index + 1}
                  onClick={() => {
                    // Open modal for regular clicks
                    setSelectedPhotoIndex(index);
                    setIsModalOpen(true);
                  }}
                  className="w-full h-full"
                />
                {/* Invisible overlay link for cmd/ctrl clicks */}
                <a
                  href={`/media/${photo.object_key}`}
                  className="absolute inset-0 z-10 pointer-events-none"
                  onClick={(e) => {
                    // Only allow cmd/ctrl/middle clicks through
                    if (!e.metaKey && !e.ctrlKey && e.button !== 1) {
                      e.preventDefault();
                    }
                  }}
                  onMouseDown={(e) => {
                    // Re-enable pointer events for cmd/ctrl/middle clicks
                    if (e.metaKey || e.ctrlKey || e.button === 1) {
                      e.currentTarget.style.pointerEvents = 'auto';
                    }
                  }}
                  onMouseUp={(e) => {
                    // Disable pointer events again
                    e.currentTarget.style.pointerEvents = 'none';
                  }}
                  aria-hidden="true"
                  tabIndex={-1}
                />
              </div>
            ))}
          </ThumbnailGrid>
            )}
          </>
        )}
        
        {/* Loading more indicator */}
        {isLoadingMore && (
          <div className="flex justify-center py-8">
            <div className="flex items-center gap-2 text-gray-600">
              <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
              <span>Loading more photos...</span>
            </div>
          </div>
        )}
      </div>
      
      {/* Media Modal */}
      <MediaModal 
        isOpen={isModalOpen} 
        onClose={handleModalClose}
        photos={photos}
        currentIndex={selectedPhotoIndex}
        onIndexChange={(newIndex) => {
          setSelectedPhotoIndex(newIndex);
        }}
        onMediaUpdate={handleMediaUpdate}
      />
    </div>
  );
}