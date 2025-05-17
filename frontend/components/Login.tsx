"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";

export default function Login() {
  const [email, setEmail] = useState("");
  const [isEligibilityChecking, setIsEligibilityChecking] = useState(false);
  const [isEligible, setIsEligible] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Router not needed for this simplified implementation
  const { login } = useAuth();

  const checkEligibility = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsEligibilityChecking(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/check-eligibility", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const result = await response.json();

      if (result.eligible) {
        setIsEligible(true);
      } else {
        setError("This email is not authorized to access the application.");
        setIsEligible(false);
      }
    } catch (error) {
      console.error("Error checking eligibility:", error);
      setError(
        "An error occurred while checking eligibility. Please try again.",
      );
    } finally {
      setIsEligibilityChecking(false);
    }
  };

  // This function is used in the form submission handler
  const handleSuccessfulAuth = async (token: string) => {
    try {
      // Exchange Stytch token for our backend session
      const authResponse = await fetch("/api/auth/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token }),
      });

      if (!authResponse.ok) {
        throw new Error("Authentication failed");
      }

      const result = await authResponse.json();
      await login(result.sessionToken, result.sessionJwt, result.userRoles);
    } catch (error) {
      console.error("Login error:", error);
      setError("Authentication failed. Please try again.");
    }
  };

  return (
    <div className="login-container max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6 text-center">Log in to Tagline</h1>

      {!isEligible ? (
        <div className="eligibility-check">
          <p className="mb-4 text-center">
            Please enter your email to verify access
          </p>

          <form onSubmit={checkEligibility} className="space-y-4">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Your email address"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isEligibilityChecking}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isEligibilityChecking ? "Checking..." : "Check Access"}
            </button>
          </form>

          {error && (
            <div className="error-message mt-4 text-red-600 text-center">
              {error}
            </div>
          )}
        </div>
      ) : (
        <div className="stytch-login-container">
          <p className="mb-4 text-center">
            Please check your email for a magic link to sign in
          </p>

          <div className="stytch-container">
            {/*
              Note: Due to API compatibility issues with the current Stytch version,
              we're implementing a custom login form instead of using the StytchLogin component.
              This will be replaced with the proper Stytch component once dependencies are resolved.
            */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                // Send magic link email manually
                fetch("/api/auth/send-magic-link", {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({ email }),
                })
                  .then((response) => response.json())
                  .then((data) => {
                    if (data.success) {
                      // Show success message
                      setError(null);
                      // If token is returned, handle authentication
                      if (data.token) {
                        handleSuccessfulAuth(data.token);
                      }
                    } else {
                      setError(data.error || "Failed to send magic link");
                    }
                  })
                  .catch((err) => {
                    console.error("Error sending magic link:", err);
                    setError("Failed to send magic link. Please try again.");
                  });
              }}
            >
              <div className="mb-4">
                <input
                  type="email"
                  value={email}
                  readOnly
                  className="w-full px-4 py-2 border border-gray-300 rounded-md bg-gray-100"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Send Magic Link
              </button>
            </form>
          </div>

          <button
            onClick={() => setIsEligible(false)}
            className="mt-4 w-full bg-gray-200 text-gray-800 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Change Email
          </button>
        </div>
      )}
    </div>
  );
}
