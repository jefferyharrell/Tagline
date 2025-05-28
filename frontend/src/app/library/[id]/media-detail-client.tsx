"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Textarea } from "@/components/ui/textarea";
import { Sheet } from "@/components/ui/sheet";
import { toast } from "sonner";
import { Lock, Unlock, ChevronLeft, ChevronRight, ArrowLeft } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    file_size?: string;
    dimensions?: string;
    created?: string;
    intrinsic?: {
      width: number;
      height: number;
    };
    [key: string]: string | string[] | object | undefined;
  };
  created_at?: string;
  updated_at?: string;
}

interface MediaDetailClientProps {
  initialMediaObject: MediaObject;
  isModal?: boolean;
  onClose?: () => void;
}

export default function MediaDetailClient({
  initialMediaObject,
  isModal = false,
  onClose,
}: MediaDetailClientProps) {
  const router = useRouter();
  const [mediaObject, setMediaObject] =
    useState<MediaObject>(initialMediaObject);
  const [description, setDescription] = useState(
    mediaObject.metadata.description || "",
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isDescriptionLocked, setIsDescriptionLocked] = useState(true);
  const [isMetadataOpen, setIsMetadataOpen] = useState(false);
  const [showSaveConfirmation, setShowSaveConfirmation] = useState(false);
  const [adjacentMedia, setAdjacentMedia] = useState<{
    previous: MediaObject | null;
    next: MediaObject | null;
  }>({ previous: null, next: null });
  const [isNavigating, setIsNavigating] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(true);
  
  // Cache for media data to avoid re-fetching
  const mediaCache = useRef<Map<string, MediaObject>>(new Map());
  
  // Track the last saved description for reverting on error
  const [lastSavedDescription, setLastSavedDescription] = useState(
    mediaObject.metadata.description || "",
  );
  
  // Track if we're in an optimistic update state
  const [isOptimisticUpdate, setIsOptimisticUpdate] = useState(false);
  
  // Cache the initial media object
  useEffect(() => {
    mediaCache.current.set(initialMediaObject.id, initialMediaObject);
  }, [initialMediaObject]);

  // Sync description when mediaObject changes
  useEffect(() => {
    setDescription(mediaObject.metadata.description || "");
    setLastSavedDescription(mediaObject.metadata.description || "");
  }, [mediaObject.metadata.description]);
  
  // Fetch media data client-side with caching
  const fetchMediaData = useCallback(async (mediaId: string) => {
    // Check cache first
    const cached = mediaCache.current.get(mediaId);
    if (cached) {
      return cached;
    }
    
    try {
      const response = await fetch(`/api/library/${mediaId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch media");
      }
      const data = await response.json();
      const mediaObject = data as MediaObject;
      
      // Cache the result
      mediaCache.current.set(mediaId, mediaObject);
      
      return mediaObject;
    } catch (error) {
      console.error("Error fetching media data:", error);
      toast.error("Failed to load media");
      return null;
    }
  }, []);
  
  // Handle browser back/forward navigation
  useEffect(() => {
    const handlePopState = async () => {
      // Extract media ID from URL
      const pathParts = window.location.pathname.split('/');
      const mediaId = pathParts[pathParts.length - 1];
      
      if (mediaId && mediaId !== mediaObject.id) {
        setIsNavigating(true);
        setImageLoaded(false);
        const newMediaData = await fetchMediaData(mediaId);
        if (newMediaData) {
          setMediaObject(newMediaData);
          setDescription(newMediaData.metadata.description || "");
          setLastSavedDescription(newMediaData.metadata.description || "");
          setIsDescriptionLocked(true);
        }
        setIsNavigating(false);
      }
    };
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [mediaObject.id, fetchMediaData]);
  
  // Fetch adjacent media when component mounts or mediaObject changes
  useEffect(() => {
    const fetchAdjacentMedia = async () => {
      try {
        const response = await fetch(`/api/library/${mediaObject.id}/adjacent`);
        if (response.ok) {
          const data = await response.json();
          setAdjacentMedia(data);
          
          // Preload adjacent images for faster navigation
          if (data.previous) {
            // Prefetch the proxy image
            const prevImg = new window.Image();
            prevImg.src = `/api/library/${data.previous.id}/proxy`;
            
            // Prefetch and cache the media data too
            fetch(`/api/library/${data.previous.id}`)
              .then(res => res.json())
              .then(mediaData => {
                mediaCache.current.set(data.previous.id, mediaData);
              })
              .catch(() => {});
          }
          
          if (data.next) {
            // Prefetch the proxy image
            const nextImg = new window.Image();
            nextImg.src = `/api/library/${data.next.id}/proxy`;
            
            // Prefetch and cache the media data too
            fetch(`/api/library/${data.next.id}`)
              .then(res => res.json())
              .then(mediaData => {
                mediaCache.current.set(data.next.id, mediaData);
              })
              .catch(() => {});
          }
        }
      } catch (error) {
        console.error("Error fetching adjacent media:", error);
      }
    };
    
    fetchAdjacentMedia();
  }, [mediaObject.id, mediaCache]);

  // Navigation functions
  const navigateToMedia = useCallback(async (media: MediaObject | null) => {
    if (!media || isNavigating) return;
    
    // Check if there are unsaved changes
    if (!isDescriptionLocked && description !== lastSavedDescription) {
      const confirmed = window.confirm("You have unsaved changes. Do you want to leave without saving?");
      if (!confirmed) return;
    }
    
    setIsNavigating(true);
    setImageLoaded(false);
    
    // Fetch the new media data
    const newMediaData = await fetchMediaData(media.id);
    if (newMediaData) {
      // Update the URL without full page reload (only in modal mode)
      if (isModal) {
        window.history.pushState({}, '', `/library/${media.id}`);
      }
      
      // Update the media object state
      setMediaObject(newMediaData);
      
      // Reset description states
      setDescription(newMediaData.metadata.description || "");
      setLastSavedDescription(newMediaData.metadata.description || "");
      setIsDescriptionLocked(true);
    }
    
    setIsNavigating(false);
  }, [isDescriptionLocked, description, lastSavedDescription, isNavigating, fetchMediaData, isModal]);
  
  const handlePrevious = useCallback(() => {
    navigateToMedia(adjacentMedia.previous);
  }, [adjacentMedia.previous, navigateToMedia]);
  
  const handleNext = useCallback(() => {
    navigateToMedia(adjacentMedia.next);
  }, [adjacentMedia.next, navigateToMedia]);

  const handleSave = async () => {
    // Start optimistic update
    setIsLoading(true);
    setIsOptimisticUpdate(true);
    
    // Save the current description as the new "last saved" optimistically
    const optimisticDescription = description;
    setLastSavedDescription(optimisticDescription);
    
    // Optimistically update the media object
    setMediaObject(prev => ({
      ...prev,
      metadata: {
        ...prev.metadata,
        description: optimisticDescription,
      },
    }));
    
    // Lock the field immediately
    setIsDescriptionLocked(true);

    const requestBody = {
      metadata: {
        ...mediaObject.metadata,
        description: optimisticDescription,
      },
    };

    try {
      const response = await fetch(`/api/library/${mediaObject.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to update media object");
      }

      const updatedMediaObject = await response.json();

      // Server confirmed - update with server response
      setMediaObject(updatedMediaObject);
      setDescription(updatedMediaObject.metadata.description || "");
      setLastSavedDescription(updatedMediaObject.metadata.description || "");
      
      // Show success message after server confirms
      toast.success("Description saved successfully");
    } catch (err) {
      console.error("PATCH - Error updating media object:", err);
      
      // Revert on error
      setMediaObject(prev => ({
        ...prev,
        metadata: {
          ...prev.metadata,
          description: mediaObject.metadata.description || "",
        },
      }));
      setDescription(mediaObject.metadata.description || "");
      setLastSavedDescription(mediaObject.metadata.description || "");
      
      // Unlock on error so user can try again
      setIsDescriptionLocked(false);
      
      toast.error((err as Error).message || "Failed to save description");
    } finally {
      setIsLoading(false);
      setIsOptimisticUpdate(false);
    }
  };

  const handleCancel = useCallback(() => {
    setDescription(lastSavedDescription);
    setIsDescriptionLocked(true);
  }, [lastSavedDescription]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Escape key to cancel editing
      if (event.key === "Escape" && !isDescriptionLocked) {
        handleCancel();
        return;
      }
      
      // Don't navigate if user is typing in textarea
      const activeElement = document.activeElement;
      if (activeElement && activeElement.tagName === "TEXTAREA") {
        return;
      }
      
      // Arrow keys for navigation
      if (event.key === "ArrowLeft") {
        handlePrevious();
      } else if (event.key === "ArrowRight") {
        handleNext();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isDescriptionLocked, handleCancel, handlePrevious, handleNext]);

  const toggleDescriptionLock = async () => {
    // If currently unlocked and about to lock, show confirmation
    if (!isDescriptionLocked) {
      setShowSaveConfirmation(true);
    } else {
      // Just unlock without saving
      setIsDescriptionLocked(false);
    }
  };

  const confirmSave = async () => {
    setShowSaveConfirmation(false);
    await handleSave();
  };

  const cancelSave = () => {
    setShowSaveConfirmation(false);
    handleCancel();
  };

  const handleBackToGallery = useCallback(() => {
    // Check if there are unsaved changes
    if (!isDescriptionLocked && description !== lastSavedDescription) {
      const confirmed = window.confirm("You have unsaved changes. Do you want to leave without saving?");
      if (!confirmed) return;
    }
    
    if (isModal && onClose) {
      onClose();
    } else {
      router.push('/library');
    }
  }, [router, isDescriptionLocked, description, lastSavedDescription, isModal, onClose]);

  return (
    <div className="min-h-screen">
      {/* Header with Back Button - only show in full page mode */}
      {!isModal && (
        <div className="sticky top-0 z-10 bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <button
                onClick={handleBackToGallery}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
                <span className="text-sm font-medium">Back to Gallery</span>
              </button>
            </div>
          </div>
        </div>
      )}
      
      <Sheet open={isMetadataOpen} onOpenChange={setIsMetadataOpen}>
        {/* Photo Section with Positioned Description */}
        <div className={`relative flex justify-center ${isModal ? 'pt-0' : 'pt-4'}`}>
          <div 
            className="relative w-full max-w-4xl"
            style={{ 
              maxHeight: '80vh',
              aspectRatio: mediaObject.metadata.intrinsic 
                ? `${mediaObject.metadata.intrinsic.width} / ${mediaObject.metadata.intrinsic.height}`
                : '4 / 3'
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/api/library/${mediaObject.id}/proxy`}
              alt={mediaObject.metadata.description || "Media preview"}
              className={`absolute inset-0 w-full h-full object-contain transition-opacity duration-300 ${imageLoaded ? "opacity-100" : "opacity-0"}`}
              onLoad={() => setImageLoaded(true)}
            />
            
            {/* Loading overlay */}
            {(isNavigating || !imageLoaded) && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-600"></div>
              </div>
            )}
            
            {/* Navigation Buttons */}
            <button
              onClick={handlePrevious}
              disabled={!adjacentMedia.previous || isNavigating}
              className={`absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-all duration-200 ${
                !adjacentMedia.previous || isNavigating
                  ? "opacity-50 cursor-not-allowed"
                  : "hover:scale-110"
              }`}
              title="Previous photo (←)"
            >
              <ChevronLeft className="h-6 w-6 text-gray-700" />
            </button>
            
            <button
              onClick={handleNext}
              disabled={!adjacentMedia.next || isNavigating}
              className={`absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-all duration-200 ${
                !adjacentMedia.next || isNavigating
                  ? "opacity-50 cursor-not-allowed"
                  : "hover:scale-110"
              }`}
              title="Next photo (→)"
            >
              <ChevronRight className="h-6 w-6 text-gray-700" />
            </button>
            
            {/* Description Section - Positioned at Bottom of Photo */}
            <div className="absolute bottom-0 left-0 right-0 p-4">
              <div className="relative">
                
                {/* Helper text and status - positioned above textarea */}
                <div className="flex justify-end mb-2 h-6">
                  {/* Helper text when editing */}
                  {!isDescriptionLocked && !isOptimisticUpdate && (
                    <p className="text-xs text-gray-500 bg-white/80 backdrop-blur-sm rounded px-2 py-1">
                      Click the lock icon to save changes, or press Escape to cancel
                    </p>
                  )}

                  {/* Subtle loading indicator for optimistic updates */}
                  {isOptimisticUpdate && (
                    <div className="flex items-center text-xs text-gray-600 bg-white/80 backdrop-blur-sm rounded px-2 py-1">
                      <svg className="animate-pulse h-3 w-3 mr-1.5 text-jl-red" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      Saving...
                    </div>
                  )}
                </div>
                
                <Textarea
                  value={description || ""}
                  onChange={(e) => setDescription(e.target.value)}
                  readOnly={isDescriptionLocked}
                  rows={3}
                  className={`!text-lg font-medium w-full resize-none bg-white/50 backdrop-blur-sm border border-gray-200 rounded-lg shadow-sm pr-12 transition-opacity duration-200 ${
                    isDescriptionLocked
                      ? "text-gray-900 cursor-default"
                      : "text-gray-900"
                  } ${isOptimisticUpdate ? "opacity-70" : ""}`}
                  placeholder={
                    isDescriptionLocked
                      ? ""
                      : "Enter a description for this media..."
                  }
                  onClick={() => {
                    if (isDescriptionLocked && !description) {
                      toggleDescriptionLock();
                    }
                  }}
                />

                {/* Padlock Icon */}
                <button
                  onClick={toggleDescriptionLock}
                  disabled={isLoading}
                  className={`absolute top-10 right-2 p-1.5 rounded-full bg-gray-100 hover:bg-gray-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-jl-red transition-all duration-200 ${
                    isLoading
                      ? "opacity-50 cursor-not-allowed"
                      : ""
                  }`}
                  title={
                    isLoading
                      ? "Saving..."
                      : isDescriptionLocked
                      ? "Click to edit description"
                      : "Click to save and lock description"
                  }
                >
                  {isLoading ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-jl-red"></div>
                  ) : isDescriptionLocked ? (
                    <Lock className="h-4 w-4 text-gray-600" />
                  ) : (
                    <Unlock className="h-4 w-4 text-jl-red" />
                  )}
                </button>
              </div>
            </div>

          </div>
        </div>

        {/* Raw Metadata Card */}
        <div className="max-w-4xl mx-auto p-4">
          <Card>
            <CardHeader>
              <CardTitle>Raw Metadata</CardTitle>
              <CardDescription>
                All available metadata for this media object
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Basic Properties */}
                <div className="">
                  <div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Object Key:</span>
                        <span className="font-mono text-xs break-all">{mediaObject.object_key}</span>
                      </div>
                    </div>
                  </div>

                </div>

                {/* Raw JSON */}
                <div className="border-t pt-4">
                  <h4 className="font-medium text-sm text-gray-700 mb-2">Raw JSON</h4>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-auto">
                    <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap">
                      {JSON.stringify(mediaObject, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Save Confirmation Dialog */}
        {showSaveConfirmation && (
          <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Save Changes?
              </h3>
              <p className="text-gray-600 mb-6">
                Are you sure you want to save the changes to this description? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={cancelSave}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmSave}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-jl-red rounded-md hover:bg-jl-red-700 focus:outline-none focus:ring-2 focus:ring-jl-red disabled:opacity-50"
                >
                  {isLoading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </div>
          </div>
        )}

      </Sheet>
    </div>
  );
}