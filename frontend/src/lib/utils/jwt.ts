import { JWTPayload } from '../types/auth';

/**
 * Decodes a JWT token without verifying its signature
 * @param token JWT token string
 * @returns Decoded JWT payload or null if invalid
 */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Error decoding JWT:', error);
    return null;
  }
}

/**
 * Checks if a JWT token is expired
 * @param token JWT token string
 * @returns true if token is expired or invalid, false otherwise
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token);
  if (!payload) return true;
  
  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
}

/**
 * Extracts user roles from a JWT token
 * @param token JWT token string
 * @returns Array of user roles or empty array if token is invalid
 */
export function getUserRolesFromToken(token: string): string[] {
  const payload = decodeJWT(token);
  if (!payload || !payload.roles) return [];
  
  return payload.roles;
}
