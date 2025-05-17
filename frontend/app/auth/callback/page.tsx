"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export default function StytchCallback() {
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();

  useEffect(() => {
    const token = searchParams.get("token");

    if (!token) {
      setError("Invalid or missing authentication token");
      return;
    }

    const authenticateWithToken = async () => {
      try {
        const response = await fetch("/api/auth/session", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          throw new Error("Authentication failed");
        }

        const result = await response.json();
        await login(result.sessionToken, result.sessionJwt, result.userRoles);

        // Redirect to dashboard after successful login
        router.push("/dashboard");
      } catch (error) {
        console.error("Authentication error:", error);
        setError("Authentication failed. Please try again.");
      }
    };

    authenticateWithToken();
  }, [searchParams, login, router]);

  return (
    <div className="auth-callback flex flex-col items-center justify-center min-h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Authenticating...</h1>
      {error ? (
        <div className="error-message text-red-600 text-center">
          <p className="mb-4">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Return to Login
          </button>
        </div>
      ) : (
        <p>Please wait while we complete your authentication...</p>
      )}
    </div>
  );
}
