"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export default function Unauthorized() {
  const router = useRouter();
  const { user, logout } = useAuth();

  return (
    <div className="unauthorized-page min-h-screen flex flex-col items-center justify-center p-4 bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
        <h1 className="text-2xl font-bold mb-4 text-red-600">Access Denied</h1>

        <p className="mb-6">
          You don&apos;t have the required permissions to access this page.
          {user && <span> You are logged in as {user.email}.</span>}
        </p>

        <div className="flex flex-col space-y-4">
          <button
            onClick={() => router.push("/")}
            className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Go to Home
          </button>

          {user && (
            <button
              onClick={logout}
              className="bg-gray-200 text-gray-800 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              Log Out
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
