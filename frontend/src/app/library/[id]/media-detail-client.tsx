"use client";

import React, { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { toast } from "sonner";
import { Lock, Unlock } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    file_size?: string;
    dimensions?: string;
    created?: string;
    intrinsic?: {
      width: number;
      height: number;
    };
    [key: string]: string | string[] | object | undefined;
  };
  created_at?: string;
  updated_at?: string;
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
  const [isDescriptionLocked, setIsDescriptionLocked] = useState(true);
  const [isMetadataOpen, setIsMetadataOpen] = useState(false);
  const [showSaveConfirmation, setShowSaveConfirmation] = useState(false);

  // Sync description when mediaObject changes
  useEffect(() => {
    setDescription(mediaObject.metadata.description || "");
  }, [mediaObject.metadata.description]);

  const handleSave = async () => {
    setIsLoading(true);

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
      toast.success("Description saved successfully");
    } catch (err) {
      console.error("PATCH - Error updating media object:", err);
      toast.error((err as Error).message || "Failed to save description");
      // Keep unlocked on error so user can try again
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = useCallback(() => {
    setDescription(mediaObject.metadata.description || "");
    setIsDescriptionLocked(true);
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
    // If currently unlocked and about to lock, show confirmation
    if (!isDescriptionLocked) {
      setShowSaveConfirmation(true);
    } else {
      // Just unlock without saving
      setIsDescriptionLocked(false);
    }
  };

  const confirmSave = async () => {
    setShowSaveConfirmation(false);
    await handleSave();
  };

  const cancelSave = () => {
    setShowSaveConfirmation(false);
    handleCancel();
  };

  return (
    <div className="min-h-screen">
      <Sheet open={isMetadataOpen} onOpenChange={setIsMetadataOpen}>
        {/* Photo Section with Positioned Description */}
        <div className="relative flex justify-center">
          <div 
            className="relative w-full max-w-4xl"
            style={{ 
              maxHeight: '80vh',
              aspectRatio: mediaObject.metadata.intrinsic 
                ? `${mediaObject.metadata.intrinsic.width} / ${mediaObject.metadata.intrinsic.height}`
                : '4 / 3'
            }}
          >
            <Image
              src={`/api/library/${mediaObject.id}/proxy`}
              alt={mediaObject.metadata.description || "Media preview"}
              fill
              className="object-contain"
              priority
            />
            
            {/* Description Section - Positioned at Bottom of Photo */}
            <div className="absolute bottom-0 left-0 right-0 p-4">
              <div className="relative">
                
                <Textarea
                  value={description || ""}
                  onChange={(e) => setDescription(e.target.value)}
                  readOnly={isDescriptionLocked}
                  rows={3}
                  className={`!text-lg font-medium w-full resize-none bg-white/50 backdrop-blur-sm border border-gray-200 rounded-lg shadow-sm pr-12 ${
                    isDescriptionLocked
                      ? "text-gray-900 cursor-default"
                      : "text-gray-900"
                  }`}
                  placeholder={
                    isDescriptionLocked
                      ? ""
                      : "Enter a description for this media..."
                  }
                  onClick={() => {
                    if (isDescriptionLocked && !description) {
                      toggleDescriptionLock();
                    }
                  }}
                />

                {/* Padlock Icon */}
                <button
                  onClick={toggleDescriptionLock}
                  disabled={isLoading}
                  className={`absolute top-2 right-2 p-1.5 rounded-full bg-gray-100 hover:bg-gray-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-jl-red ${
                    isLoading
                      ? "opacity-50 cursor-not-allowed"
                      : ""
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
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-jl-red"></div>
                  ) : isDescriptionLocked ? (
                    <Lock className="h-4 w-4 text-gray-600" />
                  ) : (
                    <Unlock className="h-4 w-4 text-jl-red" />
                  )}
                </button>

                {/* Helper text when editing */}
                {!isDescriptionLocked && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-500 bg-white/80 backdrop-blur-sm rounded px-2 py-1 inline-block">
                      Click the lock icon to save changes, or press Escape to cancel
                    </p>
                  </div>
                )}

                {/* Loading indicator when saving */}
                {isLoading && (
                  <div className="mt-2">
                    <div className="flex items-center text-xs text-gray-500 bg-white/80 backdrop-blur-sm rounded px-2 py-1 inline-block">
                      <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-jl-red mr-2"></div>
                      Saving description...
                    </div>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Raw Metadata Card */}
        <div className="max-w-4xl mx-auto p-4">
          <Card>
            <CardHeader>
              <CardTitle>Raw Metadata</CardTitle>
              <CardDescription>
                All available metadata for this media object
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Basic Properties */}
                <div className="">
                  <div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Object Key:</span>
                        <span className="font-mono text-xs break-all">{mediaObject.object_key}</span>
                      </div>
                    </div>
                  </div>

                </div>

                {/* Raw JSON */}
                <div className="border-t pt-4">
                  <h4 className="font-medium text-sm text-gray-700 mb-2">Raw JSON</h4>
                  <div className="bg-gray-50 rounded-lg p-4 overflow-auto">
                    <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap">
                      {JSON.stringify(mediaObject, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Save Confirmation Dialog */}
        {showSaveConfirmation && (
          <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Save Changes?
              </h3>
              <p className="text-gray-600 mb-6">
                Are you sure you want to save the changes to this description? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={cancelSave}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmSave}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-jl-red rounded-md hover:bg-jl-red-700 focus:outline-none focus:ring-2 focus:ring-jl-red disabled:opacity-50"
                >
                  {isLoading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </div>
          </div>
        )}

      </Sheet>
    </div>
  );
}