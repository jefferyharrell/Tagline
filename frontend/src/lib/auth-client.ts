/**
 * Client-side authentication utilities
 */

/**
 * Clear the auth cookie from client side
 */
export function clearAuthCookieClient() {
  // Clear the cookie by setting it to expire in the past
  document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
}