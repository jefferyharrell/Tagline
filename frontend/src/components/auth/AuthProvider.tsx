'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { StytchUIClient } from '@stytch/vanilla-js';
import { AuthContextType, AuthState, User } from '@/lib/types/auth';

// Create the auth context with a default value
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Initial auth state
const initialState: AuthState = {
  isLoading: true,
  isAuthenticated: false,
  user: null,
  error: null
};

// Stytch public token from environment variables
const stytchPublicToken = process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN || '';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>(initialState);
  const [stytchClient, setStytchClient] = useState<StytchUIClient | null>(null);

  // Initialize Stytch client on component mount
  useEffect(() => {
    if (typeof window !== 'undefined' && !stytchClient) {
      const client = new StytchUIClient(stytchPublicToken);
      setStytchClient(client);

      // Check if user is already authenticated
      const checkAuth = async () => {
        try {
          const { session } = await client.session.authenticate();
          // Use type assertion to work around Stytch type issues
          // This is necessary because the Stytch types may not match the actual API response
          const sessionAny = session as any;
          const token = sessionAny?.sessionToken || sessionAny?.session_token;
          if (token) {
            // Fetch user data from your API using the session token
            const response = await fetch('/api/auth/session', {
              headers: {
                Authorization: `Bearer ${token}`
              }
            });

            if (response.ok) {
              const userData = await response.json();
              setState({
                isLoading: false,
                isAuthenticated: true,
                user: userData.user,
                error: null
              });
            } else {
              // Session token is invalid or expired
              setState({
                ...initialState,
                isLoading: false
              });
            }
          } else {
            setState({
              ...initialState,
              isLoading: false
            });
          }
        } catch (error) {
          console.error('Auth check error:', error);
          setState({
            ...initialState,
            isLoading: false,
            error: 'Authentication check failed'
          });
        }
      };

      checkAuth();
    }
  }, []);

  // Check if email is eligible for login
  const checkEligibility = async (email: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/auth/verify-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      });

      const data = await response.json();
      return data.eligible;
    } catch (error) {
      console.error('Eligibility check error:', error);
      return false;
    }
  };

  // Login with email (magic link)
  const login = async (email: string): Promise<void> => {
    if (!stytchClient) {
      throw new Error('Stytch client not initialized');
    }

    // First check if the email is eligible
    const isEligible = await checkEligibility(email);
    if (!isEligible) {
      setState({
        ...state,
        error: 'This email is not eligible for access'
      });
      return;
    }

    // Send magic link using Stytch API

    // If not using mock, send real magic link
    try {
      setState({ ...state, isLoading: true, error: null });
      await stytchClient.magicLinks.email.send(email, {
        login_magic_link_url: `${window.location.origin}/auth/callback`,
        signup_magic_link_url: `${window.location.origin}/auth/callback`
      });
      setState({
        ...state,
        isLoading: false,
        error: null
      });
    } catch (error) {
      console.error('Login error:', error);
      setState({
        ...state,
        isLoading: false,
        error: 'Failed to send magic link'
      });
    }
  };

  // Logout
  const logout = async (): Promise<void> => {
    if (!stytchClient) {
      throw new Error('Stytch client not initialized');
    }

    try {
      setState({ ...state, isLoading: true });
      await stytchClient.session.revoke();
      setState({
        ...initialState,
        isLoading: false
      });
      window.location.href = '/';
    } catch (error) {
      console.error('Logout error:', error);
      setState({
        ...state,
        isLoading: false,
        error: 'Failed to logout'
      });
    }
  };

  // Auth context value
  const contextValue: AuthContextType = {
    ...state,
    login,
    logout,
    checkEligibility,
    setState
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
