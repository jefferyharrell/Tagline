import React from "react";
import Link from "next/link";

interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

interface MediaThumbnailProps {
  media: MediaObject;
}

export default function MediaThumbnail({ media }: MediaThumbnailProps) {
  const handleClick = () => {
    // Store current scroll position before navigation
    if (typeof window !== 'undefined') {
      const scrollPos = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
      sessionStorage.setItem('library-scroll-position', scrollPos.toString());
      
      // Also store the current page offset for infinite scroll
      const currentOffset = sessionStorage.getItem('library-current-offset');
      if (currentOffset) {
        sessionStorage.setItem('library-saved-offset', currentOffset);
      }
    }
  };

  return (
    <Link href={`/library/${media.id}`} className="block group" onClick={handleClick}>
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
    </Link>
  );
}