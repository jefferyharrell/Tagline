'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { StytchUIClient } from '@stytch/vanilla-js';
import { AuthContextType, AuthState, User } from '@/lib/types/auth';
import { saveAuthState, loadAuthState, clearAuthState } from '@/lib/storage';

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

  // Update state and persist to localStorage
  const updateAuthState = useCallback((newState: Partial<AuthState>) => {
    setState(prevState => {
      const updatedState = { ...prevState, ...newState };
      
      // Persist to localStorage when user is authenticated
      if (updatedState.isAuthenticated && updatedState.user) {
        saveAuthState({
          isAuthenticated: true,
          user: updatedState.user
        });
      } else if (newState.isAuthenticated === false) {
        // Clear auth state on logout
        clearAuthState();
      }
      
      return updatedState;
    });
  }, []);

  // Check if we're in mock auth mode
  const isMockAuth = process.env.NEXT_PUBLIC_MOCK_AUTH === 'true';

  // Initialize Stytch client and check auth status
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkAuth = async () => {
      try {
        // First try to load from localStorage for faster initial render
        const storedAuth = loadAuthState();
        
        if (storedAuth?.isAuthenticated && storedAuth.user) {
          // If we have a stored auth state, use it
          setState({
            isLoading: false,
            isAuthenticated: true,
            user: storedAuth.user,
            error: null
          });
          return;
        }

        // If we're in mock auth mode, don't try to authenticate with Stytch
        if (isMockAuth) {
          setState(prev => ({
            ...prev,
            isLoading: false,
            isAuthenticated: false
          }));
          return;
        }

        // Only initialize Stytch client if we're not in mock mode
        if (!stytchClient) {
          const client = new StytchUIClient(stytchPublicToken);
          setStytchClient(client);
        }

        // Verify with the server if we have a Stytch client
        if (stytchClient) {
          const { session } = await stytchClient.session.authenticate();
          const sessionAny = session as any;
          const token = sessionAny?.sessionToken || sessionAny?.session_token;
          
          if (token) {
            const response = await fetch('/api/auth/session', {
              headers: { Authorization: `Bearer ${token}` }
            });

            if (response.ok) {
              const userData = await response.json();
              updateAuthState({
                isLoading: false,
                isAuthenticated: true,
                user: userData.user,
                error: null
              });
              return;
            }
          }
        }


        // If we get here, we're not authenticated
        updateAuthState({
          ...initialState,
          isLoading: false
        });
      } catch (error) {
        console.error('Auth check error:', error);
        // Don't clear stored auth on network errors, only on auth failures
        if (error instanceof Error && error.message.includes('No session exists')) {
          clearAuthState();
        }
        updateAuthState({
          ...initialState,
          isLoading: false,
          error: 'Authentication check failed'
        });
      }
    };

    checkAuth();
  }, [updateAuthState, stytchClient, isMockAuth]);

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
      updateAuthState({
        ...state,
        error: 'This email is not eligible for access'
      });
      return;
    }

    // Send magic link using Stytch API
    try {
      updateAuthState({ ...state, isLoading: true, error: null });
      await stytchClient.magicLinks.email.send(email, {
        login_magic_link_url: `${window.location.origin}/auth/callback`,
        signup_magic_link_url: `${window.location.origin}/auth/callback`
      });
      updateAuthState({
        ...state,
        isLoading: false,
        error: null
      });
    } catch (error) {
      console.error('Login error:', error);
      updateAuthState({
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
      updateAuthState({ ...state, isLoading: true });
      await stytchClient.session.revoke();
      clearAuthState();
      updateAuthState({
        ...initialState,
        isLoading: false
      });
      window.location.href = '/';
    } catch (error) {
      console.error('Logout error:', error);
      updateAuthState({
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
