import { JwtPayload, AuthError } from '../types/auth';

const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/**
 * Decodes a JWT token without verification
 * Note: This only decodes the token, it doesn't verify the signature
 * For full verification, use verifyToken which calls the backend
 */
export function decodeToken<T = JwtPayload>(token: string): T | null {
  try {
    // Split the token into its parts
    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new AuthError('Invalid token format', 'INVALID_TOKEN');
    }

    // Decode the payload (middle part)
    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded) as T;
  } catch (error) {
    if (error instanceof AuthError) {
      throw error;
    }
    throw new AuthError('Failed to decode token', 'TOKEN_DECODE_ERROR');
  }
}

/**
 * Checks if a token is expired (client-side check only)
 */
export function isTokenExpired(token: string): boolean {
  try {
    const decoded = decodeToken<{ exp?: number }>(token);
    if (!decoded?.exp) return true;
    
    // Convert exp (seconds) to milliseconds for comparison
    return Date.now() >= decoded.exp * 1000;
  } catch {
    return true; // If we can't decode, consider it expired
  }
}

/**
 * Gets the token from storage and checks if it's expired
 */
export function getValidToken(): string | null {
  const token = getToken();
  if (!token) return null;
  
  try {
    return isTokenExpired(token) ? null : token;
  } catch {
    return null;
  }
}

/**
 * Stores the JWT token in localStorage
 */
export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (error) {
    console.error('Failed to store token:', error);
    throw new AuthError('Failed to store authentication token', 'TOKEN_STORAGE_ERROR');
  }
}

/**
 * Retrieves the JWT token from localStorage
 */
export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.error('Failed to retrieve token:', error);
    return null;
  }
}

/**
 * Removes the JWT token from localStorage
 */
export function removeToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (error) {
    console.error('Failed to remove token:', error);
  }
}

/**
 * Stores the refresh token in localStorage
 */
export function setRefreshToken(token: string): void {
  try {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } catch (error) {
    console.error('Failed to store refresh token:', error);
    throw new AuthError('Failed to store refresh token', 'TOKEN_STORAGE_ERROR');
  }
}

/**
 * Retrieves the refresh token from localStorage
 */
export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error('Failed to retrieve refresh token:', error);
    return null;
  }
}

/**
 * Removes the refresh token from localStorage
 */
export function removeRefreshToken(): void {
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error('Failed to remove refresh token:', error);
  }
}

/**
 * Clears all auth-related data from storage
 */
export function clearAuthData(): void {
  removeToken();
  removeRefreshToken();
}

/**
 * Gets the current user from the token (without verification)
 * This is useful for initial client-side state
 */
export function getUserFromToken(): JwtPayload | null {
  const token = getToken();
  if (!token) return null;

  try {
    return decodeToken<JwtPayload>(token);
  } catch {
    return null;
  }
}

/**
 * Verifies a token by sending it to the backend for validation
 * This is the proper way to verify a token's signature
 */
export async function verifyToken(token: string): Promise<boolean> {
  try {
    const response = await fetch('/api/auth/verify-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new AuthError(
        error.message || 'Token verification failed',
        error.code || 'TOKEN_VERIFICATION_FAILED'
      );
    }

    return true;
  } catch (error) {
    if (error instanceof AuthError) {
      throw error;
    }
    throw new AuthError('Failed to verify token', 'VERIFICATION_ERROR');
  }
}
