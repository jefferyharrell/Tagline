import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";
import MediaDetailClient from "./media-detail-client";

// This will handle fetching the media object on the server side
async function getMediaObject(objectKey: string) {
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    return null;
  }

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const backendApiKey = process.env.BACKEND_API_KEY;

  try {
    const response = await fetch(
      `${backendUrl}/v1/media/${encodeURIComponent(objectKey)}`,
      {
        headers: {
          Authorization: `Bearer ${authToken.value}`,
          "X-API-Key": backendApiKey || "",
        },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching media object:", error);
    return null;
  }
}

export default async function MediaDetailPage({
  params,
}: {
  params: Promise<{ object_key: string }>;
}) {
  // Await both dynamic APIs
  const cookieStore = await cookies();
  const { object_key } = await params;
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    redirect("/");
  }

  const mediaObject = await getMediaObject(object_key);

  if (!mediaObject) {
    redirect("/library");
  }

  return (
    <SidebarProvider>
      <LibrarySidebar />
      <SidebarInset className="min-h-screen bg-gray-50">
        <main className="p-6">
          <MediaDetailClient initialMediaObject={mediaObject} />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
