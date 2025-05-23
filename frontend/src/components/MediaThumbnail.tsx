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
    <Link href={`/library/${media.id}`} className="block">
      <div className="border rounded-sm overflow-hidden hover:shadow-md transition-shadow">
        <div className="relative h-48 bg-gray-200 flex items-center justify-center">
          <Image
            src={`/api/library/${media.id}/thumbnail`}
            alt={media.metadata?.description || "Media thumbnail"}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
          />
          {media.metadata?.description && (
            <div className="absolute bottom-0 left-0 right-0 bg-white/50 backdrop-blur-sm p-2">
              <p className="text-black text-sm font-medium line-clamp-2">
                {media.metadata.description}
              </p>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}