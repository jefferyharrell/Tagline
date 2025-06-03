import React from "react";
import { MediaObject } from "@/types/media";
import { Skeleton } from "@/components/ui/skeleton";

interface MediaThumbnailProps {
  media: MediaObject;
  onClick?: (media: MediaObject) => void;
}

export default function MediaThumbnail({
  media,
  onClick,
}: MediaThumbnailProps) {
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
      href={`/library/${encodeURIComponent(media.object_key)}`}
      className="block group"
      onClick={handleClick}
      target="_self"
    >
      <div className="bg-white overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 group-hover:-translate-y-1 rounded-lg">
        <div className="relative aspect-square bg-gray-100 flex items-center justify-center rounded-lg overflow-hidden">
          {media.has_thumbnail ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={`/api/library/${encodeURIComponent(media.object_key)}/thumbnail`}
              alt={media.metadata?.description || "Media thumbnail"}
              className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <>
              <Skeleton className="absolute inset-0 w-full h-full" />
              {/* Processing indicator */}
              <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20">
                <div className="text-white text-xs bg-black bg-opacity-50 px-2 py-1 rounded">
                  {media.ingestion_status === "processing"
                    ? "Processing..."
                    : "Pending..."}
                </div>
              </div>
            </>
          )}
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
