"use client";

import React from "react";
import { Image } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThumbnailGridProps {
  children?: React.ReactNode;
  className?: string;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
}

export default function ThumbnailGrid({
  children,
  className = "",
  emptyMessage = "No items to display",
  emptyIcon = <Image className="w-12 h-12 text-gray-400" />,
}: ThumbnailGridProps) {
  // Convert children to array to check if it's empty
  const childrenArray = React.Children.toArray(children);
  const hasChildren = childrenArray.length > 0;

  // Show empty state if no children
  if (!hasChildren) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-16 border-2 border-dashed border-gray-300 bg-gray-50",
          className
        )}
        role="status"
        aria-label={emptyMessage}
      >
        <div className="mb-4">{emptyIcon}</div>
        <h3 className="text-sm font-medium text-gray-900 mb-1">
          {emptyMessage}
        </h3>
      </div>
    );
  }

  // Show content state
  return (
    <div
      className={cn(
        "grid gap-6 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6",
        className
      )}
      role="grid"
    >
      {children}
    </div>
  );
}