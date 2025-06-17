'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, Loader2, AlertCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import MobilePageHeader from '@/components/MobilePageHeader';
import ThumbnailGrid from '@/components/ThumbnailGrid';
import PhotoThumbnail from '@/components/PhotoThumbnail';
import MediaModalSwiper from '@/components/MediaModalSwiper';
import { useUser } from '@/contexts/user-context';
import { clearAuthCookieClient } from '@/lib/auth-client';
import type { MediaObject } from '@/types/media';
import logger from '@/lib/logger';

interface SearchResponse {
  items: MediaObject[];
  total: number;
  limit: number;
  offset: number;
  pages: number;
}

export default function SearchClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { clearUser } = useUser();
  
  // State management
  const [searchQuery, setSearchQuery] = useState(searchParams?.get('q') || '');
  const [results, setResults] = useState<MediaObject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  
  // Modal state
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number>(-1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Refs for debouncing and infinite scroll
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  
  const LIMIT = 100;
  const DEBOUNCE_DELAY = 500;

  // Perform search
  const performSearch = useCallback(async (query: string, searchOffset: number = 0) => {
    if (!query.trim()) {
      setResults([]);
      setTotalResults(0);
      setHasMore(false);
      return;
    }

    try {
      if (searchOffset === 0) {
        setIsLoading(true);
      } else {
        setIsLoadingMore(true);
      }
      setError(null);

      const params = new URLSearchParams({
        q: query,
        limit: LIMIT.toString(),
        offset: searchOffset.toString(),
      });

      const response = await fetch(`/api/search?${params}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 401) {
          // JWT token is invalid/expired - clear user, cookie, and redirect to login
          logger.warn('Authentication failed during search, redirecting to login', 'SearchClient', {
            status: response.status,
            statusText: response.statusText
          });
          clearUser();
          clearAuthCookieClient();
          window.location.href = '/';
          return;
        }
        throw new Error('Search failed');
      }

      const data: SearchResponse = await response.json();
      
      if (searchOffset === 0) {
        setResults(data.items);
      } else {
        setResults(prev => [...prev, ...data.items]);
      }
      
      setTotalResults(data.total);
      setHasMore(data.offset + data.items.length < data.total);
      setOffset(data.offset + data.items.length);

      logger.info('Search completed', 'SearchClient', {
        query,
        results: data.items.length,
        total: data.total,
      });
    } catch (err) {
      logger.error('Search failed', 'SearchClient', { error: err });
      setError('Failed to search. Please try again.');
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, [clearUser]);

  // Handle search input changes with debouncing
  const handleSearchInputChange = useCallback((value: string) => {
    setSearchQuery(value);
    
    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Update URL immediately for better UX
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set('q', value);
    } else {
      params.delete('q');
    }
    router.push(`/search?${params.toString()}`);

    // Debounce the actual search
    searchTimeoutRef.current = setTimeout(() => {
      setOffset(0);
      performSearch(value, 0);
    }, DEBOUNCE_DELAY);
  }, [searchParams, router, performSearch]);

  // Load more results
  const loadMore = useCallback(() => {
    if (!isLoadingMore && hasMore && searchQuery) {
      performSearch(searchQuery, offset);
    }
  }, [isLoadingMore, hasMore, searchQuery, offset, performSearch]);

  // Set up infinite scroll
  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, isLoadingMore, loadMore]);

  // Initial search from URL
  useEffect(() => {
    const query = searchParams?.get('q');
    if (query && query !== searchQuery) {
      setSearchQuery(query);
      performSearch(query, 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]); // Only run on mount or when URL changes

  // Handle index change from modal
  const handleIndexChange = useCallback((newIndex: number) => {
    setSelectedPhotoIndex(newIndex);
  }, []);

  // Handle media update from modal
  const handleMediaUpdate = useCallback((updatedMedia: MediaObject) => {
    setResults(prev => prev.map(media => 
      media.object_key === updatedMedia.object_key ? updatedMedia : media
    ));
  }, []);

  return (
    <div className="min-h-screen">
      {/* Mobile Header */}
      <MobilePageHeader title="Search" />
      
      {/* Header with search input */}
      <div className="sticky top-0 z-10 bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
            <Input
              type="text"
              placeholder="Search photos by description, keywords, or filename..."
              value={searchQuery}
              onChange={(e) => handleSearchInputChange(e.target.value)}
              className="pl-10 pr-4 py-3 text-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
              autoFocus
            />
          </div>
          
          {/* Results count */}
          {!isLoading && searchQuery && totalResults > 0 && (
            <p className="mt-2 text-sm text-gray-600">
              About {totalResults.toLocaleString()} results
            </p>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <p className="mt-4 text-gray-600">Searching...</p>
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-20">
            <AlertCircle className="h-12 w-12 text-red-500" />
            <p className="mt-4 text-red-600">{error}</p>
          </div>
        )}

        {/* Empty state - no search query */}
        {!isLoading && !error && !searchQuery && (
          <div className="text-center py-20">
            <Search className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-xl text-gray-600">Enter a search term to find photos</p>
            <p className="mt-2 text-gray-500">
              Search by description, keywords, or filename
            </p>
          </div>
        )}

        {/* No results state */}
        {!isLoading && !error && searchQuery && results.length === 0 && (
          <div className="text-center py-20">
            <Search className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-xl text-gray-600">
              No photos found matching &ldquo;{searchQuery}&rdquo;
            </p>
            <p className="mt-2 text-gray-500">
              Try different keywords or check your spelling
            </p>
          </div>
        )}

        {/* Results grid */}
        {!isLoading && results.length > 0 && (
          <ThumbnailGrid>
            {results.map((photo, index) => (
              <PhotoThumbnail
                key={photo.object_key}
                media={photo}
                position={index + 1}
                onClick={() => {
                  setSelectedPhotoIndex(index);
                  setIsModalOpen(true);
                }}
              />
            ))}
          </ThumbnailGrid>
        )}

        {/* Loading more indicator */}
        {isLoadingMore && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        )}

        {/* Infinite scroll trigger */}
        <div ref={loadMoreRef} className="h-1" />
      </div>

      {/* Photo modal */}
      <MediaModalSwiper
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        photos={results}
        currentIndex={selectedPhotoIndex}
        onIndexChange={handleIndexChange}
        onMediaUpdate={handleMediaUpdate}
      />
    </div>
  );
}