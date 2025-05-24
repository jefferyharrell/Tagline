import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import PageHeader from "../components/PageHeader";
import LibrarySidebar from "@/components/LibrarySidebar";
import GalleryClient from "./gallery-client";

export default async function Gallery() {
  // Check if the user is authenticated
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <PageHeader title="" />
      <div className="flex h-[calc(100vh-4rem)]">
        <LibrarySidebar />
        <main className="flex-1 overflow-y-auto">
          <GalleryClient />
        </main>
      </div>
    </div>
  );
}
