import React from "react";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";
import { Skeleton } from "@/components/ui/skeleton";

export default function MediaDetailLoading() {
  return (
    <SidebarProvider>
      <LibrarySidebar />
      <SidebarInset className="min-h-screen bg-gray-50">
        <main className="p-6">
          <div className="min-h-screen">
            {/* Photo Section Skeleton */}
            <div className="relative flex justify-center">
              <div 
                className="relative w-full max-w-4xl"
                style={{ 
                  maxHeight: '80vh',
                  aspectRatio: '4 / 3'
                }}
              >
                {/* Image skeleton */}
                <Skeleton className="absolute inset-0" />
                
                {/* Description Section Skeleton */}
                <div className="absolute bottom-0 left-0 right-0 p-4">
                  <div className="relative">
                    {/* Status text placeholder */}
                    <div className="flex justify-end mb-2 h-6" />
                    
                    {/* Textarea skeleton */}
                    <Skeleton className="h-24 w-full rounded-lg" />
                    
                    {/* Lock button skeleton */}
                    <Skeleton className="absolute top-10 right-2 h-7 w-7 rounded-full" />
                  </div>
                </div>
              </div>
            </div>

            {/* Raw Metadata Card Skeleton */}
            <div className="max-w-4xl mx-auto p-4">
              <div className="border rounded-lg">
                <div className="p-6">
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-4 w-64" />
                </div>
              </div>
            </div>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}