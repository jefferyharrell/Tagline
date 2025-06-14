"use client";

import React, { useState, useCallback, useEffect } from "react";
import { Image, Clock, Loader, CircleX } from "lucide-react";
import { MediaObject } from "@/types/media";
import { Skeleton } from "@/components/ui/skeleton";

interface PhotoThumbnailProps {
  media: MediaObject;
  onClick: (media: MediaObject) => void;
  className?: string;
  position?: number;
}

export default function PhotoThumbnail({
  media,
  onClick,
  className = "",
  position,
}: PhotoThumbnailProps) {
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [hasImageError, setHasImageError] = useState(false);
  const [wasEverProcessing, setWasEverProcessing] = useState(
    media.ingestion_status === "pending" || media.ingestion_status === "processing"
  );

  // Track if this item ever enters processing state
  useEffect(() => {
    if (media.ingestion_status === "pending" || media.ingestion_status === "processing") {
      setWasEverProcessing(true);
    }
  }, [media.ingestion_status]);

  // Get the appropriate icon based on ingestion status
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return Clock;
      case "processing":
        return Loader;
      case "completed":
        return Image;
      case "failed":
        return CircleX;
      default:
        return Image;
    }
  };

  const handleImageLoad = useCallback(() => {
    setIsImageLoaded(true);
    setHasImageError(false);
  }, []);

  const handleImageError = useCallback(() => {
    setHasImageError(true);
    setIsImageLoaded(false);
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      // Let browser handle modifier keys naturally
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) {
        return; // Browser handles it
      }
      
      // For regular clicks, prevent navigation and trigger modal
      e.preventDefault();
      onClick(media);
    },
    [media, onClick]
  );

  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
  }, []);

  const isProcessing = media.ingestion_status === "pending" || media.ingestion_status === "processing";
  const shouldShowImage = media.has_thumbnail && !hasImageError && !isProcessing;
  
  // Only show extended processing state for items that were actually processing and now need their image to load
  const isWaitingForImageAfterProcessing = wasEverProcessing && media.ingestion_status === "completed" && media.has_thumbnail && !isImageLoaded && !hasImageError;
  
  const shouldShowSkeleton = !shouldShowImage || isWaitingForImageAfterProcessing;

  return (
    <a
      href={`/media/${encodeURIComponent(media.object_key)}`}
      className={`
        block bg-white overflow-hidden transition-all duration-200 cursor-pointer
        ${isHovered ? "shadow-md scale-105" : "shadow-sm"}
        ${className}
      `}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      aria-label={`View ${media.metadata?.description || "photo"}`}
    >
      <div className="relative aspect-square bg-gray-100 flex items-center justify-center">
        {/* Skeleton loading state */}
        {shouldShowSkeleton && (
          <div className="absolute inset-0">
            <Skeleton className="w-full h-full" />
            <div className="absolute inset-0 flex items-center justify-center">
              {(() => {
                // Show spinner ONLY if actively processing OR waiting for image after processing
                const showSpinner = media.ingestion_status === "processing" || isWaitingForImageAfterProcessing;
                const IconComponent = showSpinner ? Loader : getStatusIcon(media.ingestion_status || "completed");
                return (
                  <IconComponent 
                    className={`w-8 h-8 text-gray-300 ${showSpinner ? "animate-[spin_6s_linear_infinite]" : ""}`} 
                    aria-hidden="true" 
                  />
                );
              })()}
            </div>
          </div>
        )}

        {/* Actual thumbnail image */}
        {shouldShowImage && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={`/api/library/${encodeURIComponent(media.object_key)}/thumbnail`}
            alt={media.metadata?.description || "Photo thumbnail"}
            className={`
              absolute inset-0 w-full h-full object-cover transition-opacity duration-200
              ${isImageLoaded ? "opacity-100" : "opacity-0"}
            `}
            onLoad={handleImageLoad}
            onError={handleImageError}
            loading="lazy"
          />
        )}

        {/* Processing overlay - only show for items that are truly processing and don't have a usable thumbnail yet */}
        {isProcessing && media.has_thumbnail && hasImageError && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20">
            <div className="text-white text-xs bg-black bg-opacity-50 px-2 py-1 rounded">
              Processing...
            </div>
          </div>
        )}

        {/* Error state */}
        {hasImageError && !isProcessing && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
            <div className="text-center">
              {(() => {
                const IconComponent = getStatusIcon(media.ingestion_status || "completed");
                return (
                  <IconComponent 
                    className={`w-8 h-8 text-gray-400 mx-auto mb-1 ${media.ingestion_status === "processing" ? "" : ""}`} 
                    aria-hidden="true" 
                  />
                );
              })()}
              <div className="text-xs text-gray-500">No thumbnail</div>
            </div>
          </div>
        )}

        {/* Description overlay - only show if description exists and image is loaded */}
        {media.metadata?.description && shouldShowImage && isImageLoaded && (
          <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-black/70 to-transparent">
            <div className="absolute bottom-0 left-0 right-0 p-1">
              <div 
                className="text-white text-xs leading-tight overflow-hidden break-words text-left"
                style={{
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical'
                }}
              >
                {media.metadata.description}
              </div>
            </div>
          </div>
        )}

        {/* Position badge */}
        {position && (
          <div className="absolute top-1 right-1 bg-gray-500 text-white text-sm px-3 py-1 rounded font-medium min-w-[32px] text-center">
            {position}
          </div>
        )}
      </div>
    </a>
  );
}