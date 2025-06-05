"use client";

import React, { useEffect, useCallback, useState } from "react";
import { X, ChevronRight, Lock, Unlock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import type { MediaObject } from "@/types/media";

interface MediaModalProps {
  isOpen: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  media?: MediaObject;
  onMediaUpdate?: (updatedMedia: MediaObject) => void;
}

export default function MediaModal({
  isOpen,
  onClose,
  children,
  media,
  onMediaUpdate,
}: MediaModalProps) {
  const router = useRouter();
  const [imageLoaded, setImageLoaded] = useState(false);
  
  // Description editing state
  const [currentMedia, setCurrentMedia] = useState<MediaObject | null>(media || null);
  const [description, setDescription] = useState("");
  const [isDescriptionLocked, setIsDescriptionLocked] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [lastSavedDescription, setLastSavedDescription] = useState("");
  const [isOptimisticUpdate, setIsOptimisticUpdate] = useState(false);
  const [showSaveConfirmation, setShowSaveConfirmation] = useState(false);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen) {
        onClose();
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
  }, [isOpen, onClose]);

  // Reset image loaded state when media changes
  useEffect(() => {
    if (media) {
      setImageLoaded(false);
    }
  }, [media]);

  // Sync media and description state when media prop changes
  useEffect(() => {
    if (media) {
      setCurrentMedia(media);
      setDescription(media.metadata?.description || "");
      setLastSavedDescription(media.metadata?.description || "");
      setIsDescriptionLocked(true);
    }
  }, [media]);

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
            <div className="relative inline-block">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/library/${encodeURIComponent(currentMedia.object_key)}/proxy`}
                alt={currentMedia.metadata?.description || "Photo"}
                className={`max-w-full w-auto h-auto transition-opacity duration-300 ${imageLoaded ? "opacity-100" : "opacity-0"}`}
                style={{ maxHeight: "calc(100vh - 8rem)" }}
                onLoad={() => setImageLoaded(true)}
              />

              {/* Loading overlay */}
              {!imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 min-h-[400px] min-w-[400px]">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-600"></div>
                </div>
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
