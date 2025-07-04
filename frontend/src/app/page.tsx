"use client";

import { useStytch } from "@stytch/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import Image from "next/image";
import { toast } from "sonner";

export default function LoginPage() {
  const stytch = useStytch();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [authStatus, setAuthStatus] = useState<"idle" | "error" | "success">(
    "idle",
  );
  const [statusMessage, setStatusMessage] = useState("");
  const [isAnimating, setIsAnimating] = useState(false);
  const emailInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Check for existing authentication
    const checkAuth = async () => {
      try {
        const session = await stytch.session.getSync();
        if (session) {
          router.push("/library");
        }
      } catch (error) {
        console.error("Error checking session:", error);
      }
    };

    checkAuth();
  }, [stytch, router]);

  const checkEmailEligibility = async (
    email: string,
  ): Promise<{ isEligible: boolean; error?: string }> => {
    try {
      const response = await fetch("/api/auth/check-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const error = await response.json();
        return {
          isEligible: false,
          error: error.error || "Failed to check email eligibility",
        };
      }

      const data = await response.json();
      return { isEligible: data.eligible };
    } catch (error) {
      console.error("Error checking email eligibility:", error);
      return {
        isEligible: false,
        error: "Failed to check email eligibility. Please try again.",
      };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);

    try {
      // First check if email is eligible
      const { isEligible, error } = await checkEmailEligibility(email);

      if (!isEligible) {
        // Start fade animation
        setIsAnimating(true);
        setTimeout(() => {
          setAuthStatus("error");
          setStatusMessage(
            error ||
              "Please contact the Junior League of Los Angeles for access.",
          );
          setIsAnimating(false);
          // Select the email text after animation
          setTimeout(() => {
            if (emailInputRef.current) {
              emailInputRef.current.focus();
              emailInputRef.current.select();
            }
          }, 100);
        }, 125);
        return;
      }

      // If email is eligible, proceed with magic link
      await stytch.magicLinks.email.loginOrCreate(email, {
        login_magic_link_url: `${process.env.NEXT_PUBLIC_APP_URL}/authenticate`,
        signup_magic_link_url: `${process.env.NEXT_PUBLIC_APP_URL}/authenticate`,
        login_expiration_minutes: 10,
        signup_expiration_minutes: 10,
      });

      // Start fade animation
      setIsAnimating(true);
      setTimeout(() => {
        setAuthStatus("success");
        setStatusMessage(
          "We've sent you a magic link. It should arrive within a minute.",
        );
        setIsAnimating(false);
      }, 125);
    } catch (error) {
      console.error("Error sending magic link:", error);
      // Start fade animation
      setIsAnimating(true);
      setTimeout(() => {
        setAuthStatus("error");
        setStatusMessage(
          "Something went wrong. Please try again or contact support.",
        );
        setIsAnimating(false);
      }, 125);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex justify-center mb-6">
            <Image
              src="/JLLA_stacked_vert.svg"
              alt="Junior League of Los Angeles"
              width={200}
              height={200}
              className="w-[400px] h-[300px]"
              priority={true}
            />
          </div>
          <div
            className={`transition-opacity duration-[125ms] ${isAnimating ? "opacity-0" : "opacity-100"}`}
          >
            <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
              {authStatus === "error"
                ? "This email is not authorized"
                : authStatus === "success"
                  ? "Check your email"
                  : "Sign in to your account"}
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              {authStatus === "idle"
                ? "Enter your email to receive a magic link"
                : statusMessage}
            </p>
          </div>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email-address" className="sr-only">
                Email address
              </label>
              <input
                ref={emailInputRef}
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setAuthStatus("idle");
                  setStatusMessage("");
                }}
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                disabled={isLoading}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !email}
              className={`group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white ${
                isLoading || !email
                  ? "bg-jl-red-300"
                  : "bg-jl-red-600 hover:bg-jl-red-700"
              } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-jl-red-500`}
            >
              {isLoading ? "Sending..." : "Send Magic Link"}
            </button>
          </div>

          {/* Dev Login Button - Only visible when bypass is enabled */}
          {process.env.NEXT_PUBLIC_AUTH_BYPASS_ENABLED === "true" && (
            <div className="mt-4">
              <button
                type="button"
                onClick={async () => {
                  try {
                    setIsLoading(true);
                    const devEmail =
                      email ||
                      process.env.NEXT_PUBLIC_AUTH_BYPASS_DEFAULT_EMAIL ||
                      "";

                    if (!devEmail) {
                      toast.error(
                        "Please enter an email address for dev login",
                      );
                      setIsLoading(false);
                      return;
                    }

                    const response = await fetch("/api/auth/dev-login", {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                      },
                      body: JSON.stringify({ email: devEmail }),
                    });

                    if (!response.ok) {
                      const error = await response.json();
                      throw new Error(
                        error.message || "Development login failed",
                      );
                    }

                    // Trigger auth state change event
                    window.dispatchEvent(new Event("auth-state-change"));

                    // Redirect to library
                    router.push("/library");
                  } catch (error) {
                    console.error("Dev login error:", error);
                    toast.error(
                      (error as Error).message || "Development login failed",
                    );
                  } finally {
                    setIsLoading(false);
                  }
                }}
                disabled={isLoading || !email}
                className={`w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white ${
                  isLoading || !email
                    ? "bg-purple-300"
                    : "bg-purple-600 hover:bg-purple-700"
                } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500`}
              >
                ⚙️ Developer Login
              </button>
              <div className="mt-1 text-xs text-center text-gray-500">
                Bypasses email verification (admin use only)
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
