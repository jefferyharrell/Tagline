'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

interface User {
  id: string;
  email: string;
  firstname: string | null;
  lastname: string | null;
  roles: { id: string; name: string }[];
  is_active: boolean;
  created_at: string;
}

interface UserContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  refreshUser: () => Promise<void>;
  updateUser: (data: { firstname?: string; lastname?: string }) => Promise<void>;
  clearUser: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

// Custom event for auth state changes
export const AUTH_STATE_CHANGE_EVENT = 'auth-state-change';

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const clearUser = () => {
    setUser(null);
    setError(null);
  };

  const fetchUser = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/auth/me', {
        // Add cache busting to ensure fresh data
        cache: 'no-store',
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          // User is not authenticated
          setUser(null);
          return;
        }
        throw new Error('Failed to fetch user data');
      }

      const userData = await response.json();
      setUser(userData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error fetching user:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateUser = async (data: { firstname?: string; lastname?: string }) => {
    try {
      setError(null);
      
      const response = await fetch('/api/auth/me', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update user data');
      }

      const updatedUser = await response.json();
      setUser(updatedUser);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error updating user:', err);
      throw err;
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchUser();

    // Listen for auth state changes
    const handleAuthChange = () => {
      fetchUser();
    };

    window.addEventListener(AUTH_STATE_CHANGE_EVENT, handleAuthChange);

    return () => {
      window.removeEventListener(AUTH_STATE_CHANGE_EVENT, handleAuthChange);
    };
  }, []);

  return (
    <UserContext.Provider 
      value={{ 
        user, 
        loading, 
        error, 
        refreshUser: fetchUser,
        updateUser,
        clearUser 
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}