"use client";

import React from "react";
import { Folder } from "lucide-react";
import { cn } from "@/lib/utils";

interface FolderListProps {
  folders: FolderItem[];
  onFolderClick: (folderName: string) => void;
  className?: string;
  emptyMessage?: string;
}

interface FolderItem {
  name: string;
  is_folder: boolean;
}

// Natural sort function for alphanumeric strings
const naturalSort = (a: string, b: string): number => {
  return a.localeCompare(b, undefined, {
    numeric: true,
    sensitivity: 'base'
  });
};

export default function FolderList({
  folders,
  onFolderClick,
  className = "",
  emptyMessage = "No subfolders in this directory",
}: FolderListProps) {
  // Handle empty or invalid folders array
  if (!folders || folders.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center py-16",
          className
        )}
        role="status"
        aria-label={emptyMessage}
      >
        <div className="mb-4">
          <Folder className="w-12 h-12 text-gray-400" />
        </div>
        <h3 className="text-sm font-medium text-gray-900">
          {emptyMessage}
        </h3>
      </div>
    );
  }

  // Sort folders naturally and filter only folder items
  const sortedFolders = folders
    .filter(folder => folder.is_folder)
    .sort((a, b) => naturalSort(a.name, b.name));

  // If no folders after filtering, show empty state
  if (sortedFolders.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center py-16",
          className
        )}
        role="status"
        aria-label={emptyMessage}
      >
        <div className="mb-4">
          <Folder className="w-12 h-12 text-gray-400" />
        </div>
        <h3 className="text-sm font-medium text-gray-900">
          {emptyMessage}
        </h3>
      </div>
    );
  }

  const handleFolderClick = (folderName: string) => {
    if (onFolderClick) {
      onFolderClick(folderName);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent, folderName: string) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleFolderClick(folderName);
    }
  };

  return (
    <div
      className={cn(
        "-mx-6 overflow-hidden",
        className
      )}
      role="list"
      aria-label="Folder list"
    >
      {sortedFolders.map((folder, index) => (
        <React.Fragment key={folder.name}>
          <button
            className="w-full px-6 py-3 flex items-center gap-3 text-left hover:bg-gray-50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-jl-red focus:ring-inset"
            onClick={() => handleFolderClick(folder.name)}
            onKeyDown={(e) => handleKeyDown(e, folder.name)}
            role="listitem"
            aria-label={`Open folder ${folder.name}`}
          >
            <Folder className="w-5 h-5 text-jl-red flex-shrink-0" />
            <span className="text-gray-900 font-medium truncate">
              {folder.name}
            </span>
          </button>
          {index < sortedFolders.length - 1 && (
            <div className="mx-6 border-b border-gray-200" />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}