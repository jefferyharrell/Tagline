"use client";

import { useStytch } from "@stytch/nextjs";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";

function AuthenticateContent() {
  const stytch = useStytch();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authenticateWithToken = async () => {
      try {
        // Get token and type from URL params
        const token = searchParams.get("token");
        searchParams.get("stytch_token_type");

        if (!token) {
          setError("No authentication token found");
          setIsLoading(false);
          return;
        }

        // Send token to our backend API
        const response = await fetch("/api/auth/callback", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(
            data.message ||
              `Authentication failed with status ${response.status}`,
          );
        }

        await response.json();

        // Trigger auth state change event
        window.dispatchEvent(new Event("auth-state-change"));

        // Redirect to library on success
        router.push("/library");
      } catch (error) {
        console.error("Authentication error:", error);
        setError((error as Error).message || "Authentication failed");
        setIsLoading(false);
      }
    };

    authenticateWithToken();
  }, [stytch, router, searchParams]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-8 bg-white rounded-lg shadow-sm">
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4 mx-auto" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6 mx-auto" />
            <div className="pt-4 flex justify-center">
              <div className="flex space-x-2">
                <Skeleton className="h-2 w-2 rounded-full animate-pulse" />
                <Skeleton className="h-2 w-2 rounded-full animate-pulse delay-75" />
                <Skeleton className="h-2 w-2 rounded-full animate-pulse delay-150" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-semibold text-red-600 mb-4">
            Authentication Error
          </h1>
          <p className="text-gray-700 mb-4">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  return null;
}

export default function AuthenticatePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full p-8 bg-white rounded-lg shadow-sm">
            <div className="space-y-4">
              <Skeleton className="h-8 w-3/4 mx-auto" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6 mx-auto" />
            </div>
          </div>
        </div>
      }
    >
      <AuthenticateContent />
    </Suspense>
  );
}
