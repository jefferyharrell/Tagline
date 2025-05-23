"use client";

import React, { useState, useEffect } from "react";
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

  const handleCancel = () => {
    setDescription(mediaObject.metadata.description || "");
    setIsDescriptionLocked(true);
    setError(null);
    setSuccess(null);
  };

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
  }, [isDescriptionLocked, mediaObject.metadata.description]);

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
    <div className="max-w-4xl mx-auto">
      {/* Photo Preview Section */}
      <div className="bg-gray-100 rounded-lg overflow-hidden max-w-3xl mx-auto mb-8 relative h-144">
        <Image
          src={`/api/library/${mediaObject.id}/proxy`}
          alt={mediaObject.metadata.description || "Media preview"}
          fill
          className="object-contain"
        />
      </div>

      {/* Description Section */}
      <div className="mb-8">
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

        <div className="max-w-2xl mx-auto">
          {/* Description Textarea with Padlock */}
          <div
            className="relative"
            style={{
              width: "80%",
              margin: "0 auto",
              transform: "scale(1.5)",
              transformOrigin: "center",
            }}
          >
            <Textarea
              value={description || ""}
              onChange={(e) => setDescription(e.target.value)}
              readOnly={isDescriptionLocked}
              rows={5}
              className={`w-full resize-none ${
                isDescriptionLocked
                  ? "bg-gray-50 text-gray-700 cursor-default"
                  : "bg-white text-gray-900"
              }`}
              placeholder={
                isDescriptionLocked
                  ? description
                    ? ""
                    : "No description provided"
                  : "Enter a description for this media..."
              }
            />

            {/* Padlock Icon */}
            <button
              onClick={toggleDescriptionLock}
              disabled={isLoading}
              className={`absolute top-2 right-2 p-1 rounded focus:outline-none focus:ring-2 focus:ring-jl-red-500 ${
                isLoading
                  ? "opacity-50 cursor-not-allowed"
                  : "hover:bg-gray-100"
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
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-jl-red-600"></div>
              ) : isDescriptionLocked ? (
                <svg
                  className="h-4 w-4 text-gray-500"
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
                  className="h-4 w-4 text-jl-red-600"
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
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-500">
                Click the lock icon to save changes, or press Escape to cancel
              </p>
            </div>
          )}

          {/* Loading indicator when saving */}
          {isLoading && (
            <div className="mt-4 flex justify-center">
              <div className="flex items-center text-sm text-gray-500">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-jl-red-600 mr-2"></div>
                Saving description...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Metadata Section */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden max-w-2xl mx-auto">
        <div className="px-6 py-4 space-y-4">
          <div className="flex justify-between items-center py-3 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-500">Filename</span>
            <span className="text-sm text-gray-900 font-mono">
              {mediaObject.object_key}
            </span>
          </div>

          <div className="flex justify-between items-center py-3 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-500">
              Uploaded By
            </span>
            <div className="flex items-center">
              <div className="h-6 w-6 bg-indigo-100 rounded-full flex items-center justify-center mr-2">
                <svg
                  className="h-4 w-4 text-indigo-600"
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
              <span className="text-sm text-gray-900">System Upload</span>
            </div>
          </div>

          <div className="flex justify-between items-center py-3 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-500">
              Date Uploaded
            </span>
            <span className="text-sm text-gray-900">
              {new Date(mediaObject.created_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
              })}
            </span>
          </div>

          <div className="flex justify-between items-center py-3 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-500">File Size</span>
            <span className="text-sm text-gray-900">
              {mediaObject.metadata.file_size || "Unknown"}
            </span>
          </div>

          <div className="flex justify-between items-center py-3">
            <span className="text-sm font-medium text-gray-500">
              Dimensions
            </span>
            <span className="text-sm text-gray-900">
              {mediaObject.metadata.dimensions || "Unknown"}
            </span>
          </div>

          {/* Keywords if they exist */}
          {mediaObject.metadata.keywords &&
            mediaObject.metadata.keywords.length > 0 && (
              <div className="pt-4 border-t border-gray-200">
                <div className="flex justify-between items-start">
                  <span className="text-sm font-medium text-gray-500">
                    Keywords
                  </span>
                  <div className="flex flex-wrap gap-1 max-w-xs">
                    {mediaObject.metadata.keywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
