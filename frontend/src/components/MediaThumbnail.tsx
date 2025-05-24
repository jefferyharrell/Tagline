import React from "react";
import Link from "next/link";
import Image from "next/image";

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
  return (
    <Link href={`/library/${media.id}`} className="block group">
      <div className="bg-white overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 group-hover:-translate-y-1">
        <div className="relative h-64 bg-gray-100 flex items-center justify-center">
          <Image
            src={`/api/library/${media.id}/thumbnail`}
            alt={media.metadata?.description || "Media thumbnail"}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
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