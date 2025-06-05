"use client";

import React, { useEffect, useCallback, useState } from "react";
import { X, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MediaObject } from "@/types/media";

interface MediaModalProps {
  isOpen: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  media?: MediaObject;
}

export default function MediaModal({
  isOpen,
  onClose,
  children,
  media,
}: MediaModalProps) {
  const router = useRouter();
  const [imageLoaded, setImageLoaded] = useState(false);

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
  if (!media) return null;

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
          {/* Photo Section with Proper Scaling */}
          <div className="relative flex justify-center h-full items-center p-4">
            <div className="relative w-full h-full flex items-center justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/library/${encodeURIComponent(media.object_key)}/proxy`}
                alt={media.metadata?.description || "Photo"}
                className={`max-w-full max-h-full w-auto h-auto object-contain transition-opacity duration-300 ${imageLoaded ? "opacity-100" : "opacity-0"}`}
                style={{ maxHeight: "calc(100vh - 8rem)" }}
                onLoad={() => setImageLoaded(true)}
              />

              {/* Loading overlay */}
              {!imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-600"></div>
                </div>
              )}
            </div>
          </div>

          {/* Raw Metadata Card - Below the fold */}
          <div className="max-w-5xl mx-auto p-4 mt-4">
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
                        {media.object_key}
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
                        {JSON.stringify(media, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            
          </div>
        </div>
      </div>
    </div>
  );
}
