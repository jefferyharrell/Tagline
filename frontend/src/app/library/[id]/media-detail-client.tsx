"use client";

import React, { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { Textarea } from "@/components/ui/textarea";

interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    file_size?: string;
    dimensions?: string;
    [key: string]: string | string[] | undefined;
  };
  created_at: string;
  updated_at: string;
}

interface MediaDetailClientProps {
  initialMediaObject: MediaObject;
}

export default function MediaDetailClient({
  initialMediaObject,
}: MediaDetailClientProps) {
  const [mediaObject, setMediaObject] =
    useState<MediaObject>(initialMediaObject);
  const [description, setDescription] = useState(
    mediaObject.metadata.description || "",
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isDescriptionLocked, setIsDescriptionLocked] = useState(true);

  // Sync description when mediaObject changes
  useEffect(() => {
    setDescription(mediaObject.metadata.description || "");
  }, [mediaObject.metadata.description]);

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    const requestBody = {
      metadata: {
        ...mediaObject.metadata,
        description,
      },
    };

    try {
      const response = await fetch(`/api/library/${mediaObject.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to update media object");
      }

      const updatedMediaObject = await response.json();

      setMediaObject(updatedMediaObject);
      setIsDescriptionLocked(true);
      setSuccess("Description saved successfully");
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error("PATCH - Error updating media object:", err);
      setError((err as Error).message || "Failed to save description");
      // Keep unlocked on error so user can try again
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = useCallback(() => {
    setDescription(mediaObject.metadata.description || "");
    setIsDescriptionLocked(true);
    setError(null);
    setSuccess(null);
  }, [mediaObject.metadata.description]);

  // Handle Escape key to cancel editing
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isDescriptionLocked) {
        handleCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isDescriptionLocked, handleCancel]);

  const toggleDescriptionLock = async () => {
    // If currently unlocked and about to lock, trigger auto-save
    if (!isDescriptionLocked) {
      await handleSave();
    } else {
      // Just unlock without saving
      setIsDescriptionLocked(false);
      setError(null);
      setSuccess(null);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Error/Success Messages */}
      {error && (
        <div className="mb-4 p-4 rounded-md bg-red-50 text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-4 rounded-md bg-green-50 text-green-700">
          {success}
        </div>
      )}

      {/* Main Layout - Desktop: Photo left, metadata right | Mobile: Stacked */}
      <div className="flex flex-col lg:flex-row gap-6 h-full">
        {/* Photo Section with Overlaid Description */}
        <div className="flex-1 lg:flex-[2] relative">
          {/* Large Photo */}
          <div className="bg-gray-500 rounded-lg overflow-hidden relative aspect-[4/3] lg:aspect-auto lg:h-[80vh] min-h-[400px]">
            <Image
              src={`/api/library/${mediaObject.id}/proxy`}
              alt={mediaObject.metadata.description || "Media preview"}
              fill
              className="object-contain"
            />
            
            {/* Description Textarea Overlaid on Bottom */}
            <div className="absolute bottom-0 left-0 right-0 p-4">
              <div className="relative">
                <Textarea
                  value={description || ""}
                  onChange={(e) => setDescription(e.target.value)}
                  readOnly={isDescriptionLocked}
                  rows={3}
                  className={`w-full resize-none bg-white/90 backdrop-blur-sm border-0 rounded-lg shadow-lg ${
                    isDescriptionLocked
                      ? "text-gray-700 cursor-default"
                      : "text-gray-900"
                  }`}
                  placeholder={
                    isDescriptionLocked
                      ? description
                        ? ""
                        : "Add a description..."
                      : "Enter a description for this media..."
                  }
                />

                {/* Padlock Icon */}
                <button
                  onClick={toggleDescriptionLock}
                  disabled={isLoading}
                  className={`absolute top-2 right-2 p-1.5 rounded-full bg-white/80 backdrop-blur-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    isLoading
                      ? "opacity-50 cursor-not-allowed"
                      : "hover:bg-white/90"
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
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  ) : isDescriptionLocked ? (
                    <svg
                      className="h-4 w-4 text-gray-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="h-4 w-4 text-blue-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"
                      />
                    </svg>
                  )}
                </button>
              </div>

              {/* Helper text when editing */}
              {!isDescriptionLocked && (
                <div className="mt-2">
                  <p className="text-xs text-white/80 bg-black/20 backdrop-blur-sm rounded px-2 py-1 inline-block">
                    Click the lock icon to save changes, or press Escape to cancel
                  </p>
                </div>
              )}

              {/* Loading indicator when saving */}
              {isLoading && (
                <div className="mt-2">
                  <div className="flex items-center text-xs text-white/80 bg-black/20 backdrop-blur-sm rounded px-2 py-1 inline-block">
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></div>
                    Saving description...
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Metadata Sidebar */}
        <div className="lg:flex-1 lg:max-w-sm">
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden h-fit">
            {/* User Info Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center">
                <div className="h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                  <svg
                    className="h-6 w-6 text-indigo-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900">System Upload</div>
                  <div className="text-xs text-gray-500">
                    Uploaded: {new Date(mediaObject.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Technical Metadata */}
            <div className="px-6 py-4 space-y-4">
              <div className="space-y-3">
                <div className="flex items-center text-sm">
                  <svg className="h-4 w-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="font-medium text-gray-500">Camera:</span>
                  <span className="ml-2 text-gray-900">Canon EOS R6</span>
                </div>

                <div className="flex items-center text-sm">
                  <svg className="h-4 w-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707" />
                  </svg>
                  <span className="font-medium text-gray-500">Shutter:</span>
                  <span className="ml-2 text-gray-900">1/640s</span>
                </div>

                <div className="flex items-center text-sm">
                  <svg className="h-4 w-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  <span className="font-medium text-gray-500">Aperture:</span>
                  <span className="ml-2 text-gray-900">f/2.8</span>
                </div>

                <div className="flex items-center text-sm">
                  <svg className="h-4 w-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span className="font-medium text-gray-500">ISO:</span>
                  <span className="ml-2 text-gray-900">400</span>
                </div>

                <div className="flex items-center text-sm">
                  <svg className="h-4 w-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="font-medium text-gray-500">Location:</span>
                  <span className="ml-2 text-gray-900">New York, USA</span>
                </div>
              </div>

              {/* File Details */}
              <div className="pt-4 border-t border-gray-200 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Filename</span>
                  <span className="text-gray-900 font-mono text-xs">
                    {mediaObject.object_key}
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">File Size</span>
                  <span className="text-gray-900">
                    {mediaObject.metadata.file_size || "Unknown"}
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Dimensions</span>
                  <span className="text-gray-900">
                    {mediaObject.metadata.dimensions || "Unknown"}
                  </span>
                </div>
              </div>

              {/* Tags Section */}
              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center mb-3">
                  <svg className="h-4 w-4 text-gray-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  <span className="text-sm font-medium text-gray-500">Tags:</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                    Portrait
                  </span>
                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                    Street
                  </span>
                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                    2025
                  </span>
                </div>

                {/* Keywords from metadata if they exist */}
                {mediaObject.metadata.keywords &&
                  mediaObject.metadata.keywords.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {mediaObject.metadata.keywords.map((keyword, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
