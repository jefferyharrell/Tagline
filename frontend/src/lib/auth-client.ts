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

/**
 * Handle authentication failure by calling logout endpoint which clears cookies server-side
 */
export function handleAuthFailure() {
  // Redirect to logout endpoint which will clear the cookie and redirect to login
  window.location.href = '/api/auth/logout';
}