import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import PageHeader from "../components/PageHeader";
import Link from "next/link";

export default async function Dashboard({
  searchParams,
}: {
  searchParams: { [key: string]: string | string[] | undefined };
}) {
  // In a real implementation, we would verify the JWT and get user data
  // For now, we'll just check if the auth_token cookie exists
  const cookieStore = await cookies();
  const params = await searchParams;
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    redirect("/");
  }

  // Get error or success messages from URL parameters
  const errorMessage =
    typeof params.error === "string" ? params.error : undefined;
  const successMessage =
    typeof params.success === "string" ? params.success : undefined;

  return (
    <div className="min-h-screen bg-background">
      <PageHeader title="" />
      <main>
        <div className="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
          {/* Display error message if present */}
          {errorMessage && (
            <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-md">
              {errorMessage}
            </div>
          )}

          {/* Display success message if present */}
          {successMessage && (
            <div className="mb-4 p-4 bg-green-50 text-green-700 rounded-md">
              {successMessage}
            </div>
          )}

          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-xl font-bold mb-6">Welcome to Tagline</h2>
            <p className="text-gray-600 mb-8">
              Tagline is a media management system for the Junior League of Los
              Angeles.
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
                <h3 className="text-lg font-semibold mb-2">User Management</h3>
                <p className="text-gray-600 mb-4">
                  Manage user accounts, permissions, and access controls (coming
                  soon).
                </p>
                <span className="inline-flex items-center text-gray-400">
                  Coming Soon
                </span>
              </div>

              <div className="border border-green-100 rounded-lg p-6 hover:border-green-300 hover:shadow transition-all bg-green-50">
                <h3 className="text-lg font-semibold mb-2">Media Ingest</h3>
                <p className="text-gray-600 mb-4">
                  Scan storage for new media files and import them into the
                  system.
                </p>
                <form action="/api/ingest" method="post">
                  <button
                    type="submit"
                    className="inline-flex items-center bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-md"
                  >
                    Start Ingest
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
