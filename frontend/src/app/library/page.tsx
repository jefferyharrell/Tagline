import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import PageHeader from "../components/PageHeader";
import GalleryClient from "./gallery-client";

export default async function Gallery() {
  // Check if the user is authenticated
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-background">
      <PageHeader title="" />
      <main>
        <div className="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
          <GalleryClient />
        </div>
      </main>
    </div>
  );
}
