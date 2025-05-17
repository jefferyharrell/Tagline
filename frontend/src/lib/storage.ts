import { User, UserRole } from './types/auth';

const AUTH_STORAGE_KEY = 'tagline_auth_state';

type StoredAuthState = {
  isAuthenticated: boolean;
  user: User | null;
};

export const saveAuthState = (state: { isAuthenticated: boolean; user: User | null }) => {
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      console.error('Error saving auth state to localStorage:', error);
    }
  }
};

export const loadAuthState = (): StoredAuthState | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const storedState = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!storedState) return null;
    
    const parsedState = JSON.parse(storedState);
    
    // Validate the stored state
    if (
      parsedState && 
      typeof parsedState === 'object' && 
      'isAuthenticated' in parsedState &&
      'user' in parsedState &&
      (parsedState.user === null || (
        typeof parsedState.user === 'object' &&
        'id' in parsedState.user &&
        'email' in parsedState.user &&
        Array.isArray(parsedState.user.roles) &&
        parsedState.user.roles.every((role: any): role is UserRole => 
          ['member', 'admin', 'active', 'sustainer'].includes(role)
        )
      ))
    ) {
      return {
        isAuthenticated: parsedState.isAuthenticated,
        user: parsedState.user,
      };
    }
    return null;
  } catch (error) {
    console.error('Error loading auth state from localStorage:', error);
    return null;
  }
};

export const clearAuthState = () => {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch (error) {
      console.error('Error clearing auth state from localStorage:', error);
    }
  }
};
