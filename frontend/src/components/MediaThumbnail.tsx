import React from "react";
import { MediaObject } from "@/types/media";

interface MediaThumbnailProps {
  media: MediaObject;
  onClick?: (media: MediaObject) => void;
}

export default function MediaThumbnail({ media, onClick }: MediaThumbnailProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // Check for modifier keys - if present, let the browser handle as normal link
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) {
      // Let the browser handle it normally (open in new tab/window)
      return;
    }
    
    // Otherwise, prevent default and call onClick if provided
    if (onClick) {
      e.preventDefault();
      onClick(media);
    }
  };

  return (
    <a 
      href={`/library/${media.id}`} 
      className="block group" 
      onClick={handleClick}
      target="_self"
    >
      <div className="bg-white overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 group-hover:-translate-y-1">
        <div className="relative aspect-square bg-gray-100 flex items-center justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/library/${media.id}/thumbnail`}
            alt={media.metadata?.description || "Media thumbnail"}
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
          {media.metadata?.description && (
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
              <p className="text-white text-sm font-medium line-clamp-2 leading-relaxed">
                {media.metadata.description}
              </p>
            </div>
          )}
          
          {/* Subtle hover overlay */}
          <div className="absolute inset-0 bg-jl-red/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </div>
      </div>
    </a>
  );
}