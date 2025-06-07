"use client";

import React, { useEffect, useCallback, useState } from "react";
import { X, ChevronRight, Lock, Unlock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import type { MediaObject } from "@/types/media";

interface NavigationState {
  hasPrev: boolean;
  hasNext: boolean;
}

interface MediaModalProps {
  isOpen: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  media?: MediaObject;
  onMediaUpdate?: (updatedMedia: MediaObject) => void;
  onNavigate?: (direction: 'prev' | 'next') => void;
  navigationState?: NavigationState;
}

export default function MediaModal({
  isOpen,
  onClose,
  children,
  media,
  onMediaUpdate,
  onNavigate,
  navigationState,
}: MediaModalProps) {
  const router = useRouter();
  const [imageLoaded, setImageLoaded] = useState(false);
  
  // Description editing state
  const [currentMedia, setCurrentMedia] = useState<MediaObject | null>(media || null);
  const [description, setDescription] = useState(media?.metadata?.description || "");
  const [isDescriptionLocked, setIsDescriptionLocked] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [lastSavedDescription, setLastSavedDescription] = useState(media?.metadata?.description || "");
  const [isOptimisticUpdate, setIsOptimisticUpdate] = useState(false);
  const [showSaveConfirmation, setShowSaveConfirmation] = useState(false);

  // Touch gesture state
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);
  const [swipeProgress, setSwipeProgress] = useState(0);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [isSwipeActive, setIsSwipeActive] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Swipe configuration
  const minSwipeDistance = 80; // Increased threshold for better feel

  // Navigation handlers with smooth transitions
  const handleLeftClick = useCallback(() => {
    if (navigationState?.hasPrev && onNavigate && !isTransitioning) {
      setIsTransitioning(true);
      setSwipeDirection('right');
      setSwipeProgress(1);
      
      // Brief slide animation then navigate
      setTimeout(() => {
        onNavigate('prev');
        setIsTransitioning(false);
        setSwipeDirection(null);
        setSwipeProgress(0);
      }, 200);
    }
  }, [navigationState, onNavigate, isTransitioning]);

  const handleRightClick = useCallback(() => {
    if (navigationState?.hasNext && onNavigate && !isTransitioning) {
      setIsTransitioning(true);
      setSwipeDirection('left');
      setSwipeProgress(1);
      
      // Brief slide animation then navigate
      setTimeout(() => {
        onNavigate('next');
        setIsTransitioning(false);
        setSwipeDirection(null);
        setSwipeProgress(0);
      }, 200);
    }
  }, [navigationState, onNavigate, isTransitioning]);

  // Touch handlers for swipe navigation with visual feedback
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.targetTouches[0];
    setTouchStart({ x: touch.clientX, y: touch.clientY });
    setTouchEnd(null);
    setIsSwipeActive(true);
    setSwipeProgress(0);
    setSwipeDirection(null);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const touch = e.targetTouches[0];
    setTouchEnd({ x: touch.clientX, y: touch.clientY });
    
    if (touchStart) {
      const deltaX = touch.clientX - touchStart.x;
      const deltaY = touch.clientY - touchStart.y;
      
      // Only track horizontal swipes (ignore mostly vertical swipes)
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        const direction = deltaX > 0 ? 'right' : 'left';
        const distance = Math.abs(deltaX);
        const progress = Math.min(distance / minSwipeDistance, 1);
        
        // Check if this direction is allowed
        const canSwipe = (direction === 'right' && navigationState?.hasPrev) || 
                        (direction === 'left' && navigationState?.hasNext);
        
        if (canSwipe) {
          setSwipeDirection(direction);
          setSwipeProgress(progress);
        } else {
          // Reduced movement for disabled directions
          setSwipeDirection(direction);
          setSwipeProgress(Math.min(progress * 0.3, 0.3));
        }
      }
    }
  }, [touchStart, navigationState, minSwipeDistance]);

  const handleTouchEnd = useCallback(() => {
    if (!touchStart || !touchEnd) {
      setIsSwipeActive(false);
      setSwipeProgress(0);
      setSwipeDirection(null);
      return;
    }
    
    const deltaX = touchEnd.x - touchStart.x;
    const deltaY = touchEnd.y - touchStart.y;
    
    // Only consider horizontal swipes (ignore mostly vertical swipes)
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
      if (deltaX > 0 && navigationState?.hasPrev) {
        // Swipe right - go to previous
        setIsTransitioning(true);
        setTimeout(() => {
          handleLeftClick();
          setIsTransitioning(false);
          setIsSwipeActive(false);
          setSwipeProgress(0);
          setSwipeDirection(null);
        }, 150);
      } else if (deltaX < 0 && navigationState?.hasNext) {
        // Swipe left - go to next
        setIsTransitioning(true);
        setTimeout(() => {
          handleRightClick();
          setIsTransitioning(false);
          setIsSwipeActive(false);
          setSwipeProgress(0);
          setSwipeDirection(null);
        }, 150);
      } else {
        // Snap back - incomplete or invalid swipe
        setIsSwipeActive(false);
        setTimeout(() => {
          setSwipeProgress(0);
          setSwipeDirection(null);
        }, 200);
      }
    } else {
      // Not a horizontal swipe - reset
      setIsSwipeActive(false);
      setTimeout(() => {
        setSwipeProgress(0);
        setSwipeDirection(null);
      }, 200);
    }
    
    setTouchStart(null);
    setTouchEnd(null);
  }, [touchStart, touchEnd, handleLeftClick, handleRightClick, navigationState, minSwipeDistance]);

  // Handle ESC key to close modal and arrow keys for navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen) {
        onClose();
      } else if (event.key === "ArrowLeft" && isOpen && isDescriptionLocked) {
        // Only navigate if not editing description
        handleLeftClick();
      } else if (event.key === "ArrowRight" && isOpen && isDescriptionLocked) {
        // Only navigate if not editing description
        handleRightClick();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      // Prevent background scrolling when modal is open
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose, handleLeftClick, handleRightClick, isDescriptionLocked]);

  // Reset image loaded state when media object key changes
  useEffect(() => {
    if (media && (!currentMedia || media.object_key !== currentMedia.object_key)) {
      setImageLoaded(false);
    }
  }, [media, currentMedia]);

  // Sync media and description state when media prop changes
  useEffect(() => {
    if (media && (!currentMedia || media.object_key !== currentMedia?.object_key)) {
      // Only update if it's a different media object
      setCurrentMedia(media);
      setDescription(media.metadata?.description || "");
      setLastSavedDescription(media.metadata?.description || "");
      setIsDescriptionLocked(true);
    }
  }, [media, currentMedia]);

  // Description editing functions - define handleCancel first
  const handleCancel = useCallback(() => {
    setDescription(lastSavedDescription);
    setIsDescriptionLocked(true);
  }, [lastSavedDescription]);

  // Handle ESC key for description editing
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Escape key to cancel editing
      if (event.key === "Escape" && !isDescriptionLocked) {
        handleCancel();
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isDescriptionLocked, handleCancel]);

  // Description editing functions
  const handleSave = async () => {
    if (!currentMedia) return;

    // Start optimistic update
    setIsLoading(true);
    setIsOptimisticUpdate(true);

    // Save the current description as the new "last saved" optimistically
    const optimisticDescription = description;
    setLastSavedDescription(optimisticDescription);

    // Optimistically update the media object
    const updatedMedia = {
      ...currentMedia,
      metadata: {
        ...currentMedia.metadata,
        description: optimisticDescription,
      },
    };
    setCurrentMedia(updatedMedia);

    // Lock the field immediately
    setIsDescriptionLocked(true);

    const requestBody = {
      metadata: {
        ...(currentMedia.metadata || {}),
        description: optimisticDescription,
      },
    };

    try {
      const response = await fetch(
        `/api/library/${encodeURIComponent(currentMedia.object_key)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to update media object");
      }

      const serverUpdatedMedia = await response.json();

      // Server confirmed - update with server response
      setCurrentMedia(serverUpdatedMedia);
      setDescription(serverUpdatedMedia.metadata?.description || "");
      setLastSavedDescription(serverUpdatedMedia.metadata?.description || "");

      // Notify parent component of the update
      if (onMediaUpdate) {
        onMediaUpdate(serverUpdatedMedia);
      }

      // Show success message after server confirms
      toast.success("Description saved successfully");
    } catch (err) {
      console.error("PATCH - Error updating media object:", err);

      // Revert on error
      setCurrentMedia(currentMedia);
      setDescription(currentMedia.metadata?.description || "");
      setLastSavedDescription(currentMedia.metadata?.description || "");

      // Unlock on error so user can try again
      setIsDescriptionLocked(false);

      toast.error((err as Error).message || "Failed to save description");
    } finally {
      setIsLoading(false);
      setIsOptimisticUpdate(false);
    }
  };

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

  // Handle backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  if (!isOpen) return null;

  // If children are provided, use the legacy mode
  if (children) {
    return (
      <div
        className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm"
        onClick={handleBackdropClick}
      >
        <div className="fixed inset-2 sm:inset-3 md:inset-4 lg:inset-6 xl:inset-8 bg-white rounded-lg shadow-2xl overflow-hidden">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 sm:top-4 sm:right-4 z-10 p-2 bg-white/90 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-all duration-200 hover:scale-110"
            aria-label="Close modal"
          >
            <X className="h-5 w-5 sm:h-6 sm:w-6 text-gray-700" />
          </button>

          {/* Modal content */}
          <div className="h-full overflow-auto">{children}</div>
        </div>
      </div>
    );
  }

  // New media-focused mode
  if (!currentMedia) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="fixed inset-2 sm:inset-3 md:inset-4 lg:inset-6 xl:inset-8 bg-white rounded-lg shadow-2xl overflow-hidden">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 sm:top-4 sm:right-4 z-10 p-2 bg-white/90 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-all duration-200 hover:scale-110"
          aria-label="Close modal"
        >
          <X className="h-5 w-5 sm:h-6 sm:w-6 text-gray-700" />
        </button>

        {/* Modal content */}
        <div className="h-full overflow-auto">
          {/* Photo and Content Container */}
          <div className="p-4 min-h-full flex flex-col items-center">
            {/* Photo with Description Overlay */}
            <div 
              className="relative inline-block overflow-hidden"
              onTouchStart={onNavigate ? handleTouchStart : undefined}
              onTouchMove={onNavigate ? handleTouchMove : undefined}
              onTouchEnd={onNavigate ? handleTouchEnd : undefined}
            >
              {/* Swipe overlay background */}
              {isSwipeActive && swipeProgress > 0 && (
                <div 
                  className={`absolute inset-0 z-0 transition-opacity duration-100 ${(() => {
                    // Check if this direction is allowed
                    const canSwipe = (swipeDirection === 'right' && navigationState?.hasPrev) || 
                                    (swipeDirection === 'left' && navigationState?.hasNext);
                    
                    if (!canSwipe) {
                      return swipeDirection === 'right' ? 'bg-gradient-to-r from-red-500/20 to-transparent' : 
                                                         'bg-gradient-to-l from-red-500/20 to-transparent';
                    }
                    
                    return swipeDirection === 'right' ? 'bg-gradient-to-r from-blue-500/20 to-transparent' : 
                                                       'bg-gradient-to-l from-green-500/20 to-transparent';
                  })()}`}
                  style={{ opacity: Math.min(swipeProgress, 0.6) }}
                />
              )}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/library/${encodeURIComponent(currentMedia.object_key)}/proxy`}
                alt={currentMedia.metadata?.description || "Photo"}
                className={`max-w-full w-auto h-auto transition-opacity duration-300 ${imageLoaded ? "opacity-100" : "opacity-0"} ${
                  isSwipeActive ? 'transition-none' : 'transition-transform duration-300 ease-out'
                }`}
                style={{ 
                  maxHeight: "calc(100vh - 8rem)",
                  transform: isSwipeActive && swipeDirection ? 
                    `translateX(${swipeDirection === 'right' ? '' : '-'}${Math.min(swipeProgress * 80, 40)}px) scale(${1 - Math.min(swipeProgress * 0.02, 0.02)})` : 
                    isTransitioning && swipeDirection ?
                    `translateX(${swipeDirection === 'right' ? '' : '-'}60px) scale(0.98)` :
                    'translateX(0) scale(1)'
                }}
                onLoad={() => setImageLoaded(true)}
              />

              {/* Loading overlay */}
              {!imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 min-h-[400px] min-w-[400px]">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-600"></div>
                </div>
              )}

              {/* Swipe progress indicator */}
              {isSwipeActive && swipeProgress > 0.2 && swipeDirection && (
                <div className={`absolute ${swipeDirection === 'right' ? 'left-4' : 'right-4'} top-1/2 -translate-y-1/2 z-10 pointer-events-none`}>
                  {(() => {
                    // Check if this direction is allowed
                    const canSwipe = (swipeDirection === 'right' && navigationState?.hasPrev) || 
                                    (swipeDirection === 'left' && navigationState?.hasNext);
                    
                    if (!canSwipe) {
                      // Show red X for disabled directions
                      return (
                        <div className="bg-red-500 text-white rounded-full p-2 animate-pulse scale-110">
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </div>
                      );
                    }
                    
                    // Show normal progress indicator for valid directions
                    return (
                      <>
                        <div className={`rounded-full p-2 transition-all duration-100 ${
                          swipeProgress >= 1 
                            ? 'bg-green-500 text-white animate-pulse scale-110' 
                            : 'bg-black/50 text-white/70 scale-100'
                        }`}>
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                              d={swipeDirection === 'right' ? "M15 19l-7-7 7-7" : "M9 5l7 7-7 7"} />
                          </svg>
                        </div>
                        {/* Progress arc */}
                        <div className="absolute inset-0 -m-1">
                          <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
                            <circle 
                              cx="20" cy="20" r="18" 
                              fill="none" 
                              stroke="rgba(255,255,255,0.3)" 
                              strokeWidth="2"
                            />
                            <circle 
                              cx="20" cy="20" r="18" 
                              fill="none" 
                              stroke={swipeProgress >= 1 ? "#10b981" : "rgba(255,255,255,0.8)"} 
                              strokeWidth="2"
                              strokeDasharray={`${Math.min(swipeProgress, 1) * 113} 113`}
                              className="transition-all duration-100"
                            />
                          </svg>
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}

              {/* Navigation zones - only show when navigation is available */}
              {onNavigate && navigationState && (
                <>
                  {/* Left navigation zone */}
                  <div 
                    className={`absolute left-0 top-0 bottom-0 w-1/5 cursor-pointer group ${
                      navigationState.hasPrev ? 'hover:bg-black/10' : 'cursor-not-allowed opacity-50'
                    }`}
                    onClick={navigationState.hasPrev ? handleLeftClick : undefined}
                  >
                    {/* Left arrow indicator - shows on hover */}
                    {navigationState.hasPrev && (
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <div className="bg-black/70 text-white rounded-full p-2">
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                          </svg>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right navigation zone */}
                  <div 
                    className={`absolute right-0 top-0 bottom-0 w-1/5 cursor-pointer group ${
                      navigationState.hasNext ? 'hover:bg-black/10' : 'cursor-not-allowed opacity-50'
                    }`}
                    onClick={navigationState.hasNext ? handleRightClick : undefined}
                  >
                    {/* Right arrow indicator - shows on hover */}
                    {navigationState.hasNext && (
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <div className="bg-black/70 text-white rounded-full p-2">
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Description Section - Positioned at Bottom of Photo */}
              <div className="absolute bottom-0 left-0 right-0 p-4">
                <div className="relative max-w-3xl mx-auto">
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
                        <svg
                          className="animate-pulse h-3 w-3 mr-1.5 text-jl-red"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
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
                      isLoading ? "opacity-50 cursor-not-allowed" : ""
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

            {/* Raw Metadata Card - Below the photo */}
            <div className="max-w-5xl w-full mt-8">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Raw Metadata</CardTitle>
                <CardDescription>
                  All available metadata for this media object
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Basic Properties */}
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Object Key:</span>
                      <span className="font-mono text-xs break-all">
                        {currentMedia.object_key}
                      </span>
                    </div>
                  </div>

                  {/* Raw JSON */}
                  <div className="border-t pt-4">
                    <h4 className="font-medium text-sm text-gray-700 mb-2">
                      Raw JSON
                    </h4>
                    <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-64">
                      <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap">
                        {JSON.stringify(currentMedia, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* View Full Details Link */}
            <div className="pt-4 border-t mt-6">
              <a
                href={`/media/${currentMedia.object_key}`}
                className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
                onClick={(e) => {
                  e.preventDefault();
                  router.push(`/media/${currentMedia.object_key}`);
                  onClose();
                }}
              >
                View Full Details
                <ChevronRight className="w-4 h-4 ml-1" />
              </a>
            </div>
          </div>
          </div>

          {/* Save Confirmation Dialog */}
          {showSaveConfirmation && (
            <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
              <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Save Changes?
                </h3>
                <p className="text-gray-600 mb-6">
                  Are you sure you want to save the changes to this description?
                  This action cannot be undone.
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
        </div>
      </div>
    </div>
  );
}
