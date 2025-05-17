"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { StytchLogin, useStytchUser, useStytchSession } from "@stytch/nextjs";
import { useRouter } from "next/navigation";
import { AuthContextType, AuthState, User } from "@/types/auth";

// Create the context with a default value
const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const router = useRouter();
  const { user: stytchUser, isInitialized } = useStytchUser();
  const session = useStytchSession();

  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    error: null,
  });

  // Check session on mount and when auth state changes
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // If we have a Stytch user but no session, redirect to login
        if (stytchUser && !session) {
          setState((prev) => ({ ...prev, isLoading: false }));
          router.push("/login");
          return;
        }

        // If we have a session, get user data
        if (session) {
          // TODO: Replace with actual API call to get user data
          // This is a mock implementation
          const userResponse = await fetch("/api/auth/session");
          if (userResponse.ok) {
            const userData = await userResponse.json();
            setState({
              user: userData,
              isLoading: false,
              error: null,
            });
          } else {
            throw new Error("Failed to fetch user data");
          }
        } else {
          setState((prev) => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error("Auth error:", error);
        setState({
          user: null,
          isLoading: false,
          error: error instanceof Error ? error.message : "An error occurred",
        });
      }
    };

    if (isInitialized) {
      checkAuth();
    }
  }, [stytchUser, session, isInitialized, router]);

  const login = async (email: string): Promise<void> => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      // First check if email is eligible
      const eligibilityResponse = await fetch("/api/auth/check-eligibility", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!eligibilityResponse.ok) {
        const error = await eligibilityResponse.json();
        throw new Error(error.message || "Email not eligible for access");
      }

      // If eligible, initiate Stytch magic link flow
      // This will be handled by the StytchLogin component
      // We'll just set a loading state here
    } catch (error) {
      console.error("Login error:", error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : "Login failed",
      }));
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      setState((prev) => ({ ...prev, isLoading: true }));

      // Call logout API
      await fetch("/api/auth/logout", { method: "POST" });

      // Clear local state
      setState({
        user: null,
        isLoading: false,
        error: null,
      });

      // Redirect to login
      router.push("/login");
    } catch (error) {
      console.error("Logout error:", error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: "Failed to log out",
      }));
    }
  };

  const checkSession = async (): Promise<void> => {
    try {
      setState((prev) => ({ ...prev, isLoading: true }));

      const response = await fetch("/api/auth/session");
      if (response.ok) {
        const userData = await response.json();
        setState({
          user: userData,
          isLoading: false,
          error: null,
        });
      } else {
        throw new Error("Not authenticated");
      }
    } catch (error) {
      setState({
        user: null,
        isLoading: false,
        error: error instanceof Error ? error.message : "Session check failed",
      });
    }
  };

  const hasRole = (role: string): boolean => {
    return state.user?.roles.includes(role as any) || false;
  };

  const hasAnyRole = (roles: string[]): boolean => {
    if (!state.user) return false;
    return roles.some((role) => state.user?.roles.includes(role as any));
  };

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    checkSession,
    hasRole,
    hasAnyRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
