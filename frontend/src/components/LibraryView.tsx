'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { ChevronRight, Home, AlertCircle, RefreshCw } from 'lucide-react';
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator } from '@/components/ui/breadcrumb';
import FolderList from './FolderList';
import ThumbnailGrid from './ThumbnailGrid';
import PhotoThumbnail from './PhotoThumbnail';
import MediaModal from './MediaModal';
import type { MediaObject } from '@/types/media';

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
  const [selectedPhoto, setSelectedPhoto] = useState<MediaObject | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Fetch data from API
  const fetchData = useCallback(async (path: string[]) => {
    setError(null);
    
    try {
      const pathString = path.join('/');
      const response = await fetch(`/api/library?path=${encodeURIComponent(pathString)}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load library: ${response.statusText}`);
      }
      
      const data: BrowseResponse = await response.json();
      setFolders(data.folders || []);
      setPhotos(data.media_objects || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred loading the library');
      console.error('Library fetch error:', err);
    }
  }, []);
  
  // Update URL when path changes
  useEffect(() => {
    const pathString = currentPath.join('/');
    const url = pathString ? `/library/${pathString}` : '/library';
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
    setSelectedPhoto(null);
  }, []);
  
  // Retry failed load
  const handleRetry = useCallback(() => {
    fetchData(currentPath);
  }, [currentPath, fetchData]);
  
  // Render breadcrumb navigation
  const renderBreadcrumbs = () => (
    <Breadcrumb className="mb-6">
      <BreadcrumbList>
        <BreadcrumbItem>
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
        </BreadcrumbItem>
        
        {currentPath.map((segment, index) => (
          <React.Fragment key={index}>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <button onClick={() => handleBreadcrumbClick(index)}>
                  {decodeURIComponent(segment)}
                </button>
              </BreadcrumbLink>
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
    <div className={`p-6 ${className}`}>
      {/* Breadcrumb Navigation */}
      {renderBreadcrumbs()}
      
      {/* Folder List */}
      {folders.length > 0 && (
        <div className="mb-6">
          <FolderList
            folders={folders}
            onFolderClick={handleFolderClick}
          />
        </div>
      )}
      
      {/* Photo Grid */}
      {photos.length > 0 && (
        <ThumbnailGrid>
          {photos.map((photo) => (
            <div key={photo.object_key} className="relative aspect-square">
              <PhotoThumbnail
                media={photo}
                onClick={() => {
                  // Open modal for regular clicks
                  setSelectedPhoto(photo);
                  setIsModalOpen(true);
                }}
                className="w-full h-full"
              />
              {/* Invisible overlay link for cmd/ctrl clicks */}
              <a
                href={`/media/${photo.object_key}`}
                className="absolute inset-0 z-10"
                onClick={(e) => {
                  // Only allow cmd/ctrl/middle clicks through
                  if (!e.metaKey && !e.ctrlKey && e.button !== 1) {
                    e.preventDefault();
                  }
                }}
                aria-hidden="true"
                tabIndex={-1}
              />
            </div>
          ))}
        </ThumbnailGrid>
      )}
      
      {/* Media Modal */}
      {selectedPhoto && (
        <MediaModal isOpen={isModalOpen} onClose={handleModalClose}>
          <div className="max-w-4xl mx-auto p-6">
            {/* Photo Display */}
            <div className="mb-6 relative" style={{ minHeight: '400px' }}>
              <Image
                src={`/api/library/${selectedPhoto.object_key}/proxy`}
                alt={selectedPhoto.metadata?.description || 'Photo'}
                width={800}
                height={600}
                className="w-full h-auto rounded-lg shadow-lg"
                style={{ objectFit: 'contain' }}
                priority
              />
            </div>
            
            {/* Photo Details */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-gray-900">
                {selectedPhoto.object_key.split('/').pop()}
              </h2>
              
              {selectedPhoto.metadata?.description && (
                <p className="text-gray-700">{selectedPhoto.metadata.description}</p>
              )}
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-semibold text-gray-600">Status:</span>{' '}
                  <span className="capitalize">{selectedPhoto.ingestion_status}</span>
                </div>
                
                {selectedPhoto.file_size && (
                  <div>
                    <span className="font-semibold text-gray-600">Size:</span>{' '}
                    {(selectedPhoto.file_size / 1024 / 1024).toFixed(2)} MB
                  </div>
                )}
                
                {selectedPhoto.metadata?.intrinsic && (
                  <>
                    <div>
                      <span className="font-semibold text-gray-600">Dimensions:</span>{' '}
                      {selectedPhoto.metadata.intrinsic.width} x {selectedPhoto.metadata.intrinsic.height}
                    </div>
                    
                    {selectedPhoto.metadata.intrinsic.format && (
                      <div>
                        <span className="font-semibold text-gray-600">Format:</span>{' '}
                        {selectedPhoto.metadata.intrinsic.format}
                      </div>
                    )}
                  </>
                )}
              </div>
              
              {selectedPhoto.metadata?.keywords && selectedPhoto.metadata.keywords.length > 0 && (
                <div>
                  <span className="font-semibold text-gray-600">Keywords:</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedPhoto.metadata.keywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* View Full Details Link */}
              <div className="pt-4 border-t">
                <a
                  href={`/media/${selectedPhoto.object_key}`}
                  className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
                  onClick={(e) => {
                    e.preventDefault();
                    router.push(`/media/${selectedPhoto.object_key}`);
                    handleModalClose();
                  }}
                >
                  View Full Details
                  <ChevronRight className="w-4 h-4 ml-1" />
                </a>
              </div>
            </div>
          </div>
        </MediaModal>
      )}
    </div>
  );
}