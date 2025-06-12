import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";
import Link from "next/link";
import DashboardClient from "./dashboard-client";
import { verifyJwtToken } from "@/lib/jwt-utils";

export default async function Dashboard({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  // Check if the user is authenticated with a valid token
  const cookieStore = await cookies();
  const params = await searchParams;
  const authToken = cookieStore.get("auth_token");

  if (!authToken?.value) {
    redirect("/");
  }

  // Verify the JWT token is valid
  const payload = await verifyJwtToken(authToken.value);
  if (!payload) {
    redirect("/");
  }

  // Get error or success messages from URL parameters
  const errorMessage =
    typeof params.error === "string" ? params.error : undefined;
  const successMessage =
    typeof params.success === "string" ? params.success : undefined;

  return (
    <SidebarProvider>
      <LibrarySidebar />
      <SidebarInset className="min-h-screen bg-gray-50">
        <DashboardClient
          errorMessage={errorMessage}
          successMessage={successMessage}
        />
        <main>
          <div className="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h2 className="text-xl font-bold mb-6">Welcome to Tagline</h2>
              <p className="text-gray-600 mb-8">
                Tagline is a media management system for the Junior League of
                Los Angeles.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-gray-200 rounded-lg p-6 hover:border-indigo-300 hover:shadow transition-all">
                  <h3 className="text-lg font-semibold mb-2">Media Gallery</h3>
                  <p className="text-gray-600 mb-4">
                    Browse, search, and manage your media objects with tags and
                    metadata.
                  </p>
                  <Link
                    href="/library"
                    className="inline-flex items-center text-indigo-600 hover:text-indigo-800"
                  >
                    Go to Gallery
                    <svg
                      className="w-4 h-4 ml-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M9 5l7 7-7 7"
                      ></path>
                    </svg>
                  </Link>
                </div>

                <div className="border border-gray-200 rounded-lg p-6 hover:border-indigo-300 hover:shadow transition-all">
                  <h3 className="text-lg font-semibold mb-2">
                    User Management
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Manage user accounts, permissions, and access controls.
                  </p>
                  <Link
                    href="/admin/users"
                    className="inline-flex items-center text-indigo-600 hover:text-indigo-800"
                  >
                    Manage Users
                    <svg
                      className="w-4 h-4 ml-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M9 5l7 7-7 7"
                      ></path>
                    </svg>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
