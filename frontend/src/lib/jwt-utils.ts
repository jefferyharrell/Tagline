import { cookies } from "next/headers";
import { NextRequest } from "next/server";
import type { JWTVerifyResult } from "jose";

// JWT token interface
export interface JwtPayload {
  user_id: string;
  email: string;
  firstname: string | null;
  lastname: string | null;
  roles: string[];
  exp: number;
}

/**
 * Get the JWT token from cookies or authorization header
 */
export function getJwtToken(request: NextRequest): string | null {
  // Try to get from cookie first
  const token = request.cookies.get("auth_token")?.value;
  if (token) return token;

  // Try to get from Authorization header
  const authHeader = request.headers.get("Authorization");
  if (authHeader && authHeader.startsWith("Bearer ")) {
    return authHeader.substring(7);
  }

  return null;
}

/**
 * Verify a JWT token and return the payload
 */
export async function verifyJwtToken(
  token: string,
): Promise<JwtPayload | null> {
  try {
    // Dynamically import jose to avoid build issues
    const { jwtVerify } = await import("jose");

    const { payload } = (await jwtVerify(
      token,
      new TextEncoder().encode(process.env.JWT_SECRET || ""),
    )) as JWTVerifyResult;

    return payload as unknown as JwtPayload;
  } catch (error) {
    console.error("JWT verification failed:", error);
    return null;
  }
}

/**
 * Get the current user from the JWT token in the request
 */
export async function getCurrentUser(request: NextRequest) {
  const token = getJwtToken(request);
  if (!token) return null;

  const payload = await verifyJwtToken(token);
  if (!payload) return null;

  return {
    id: payload.user_id,
    email: payload.email,
    firstname: payload.firstname,
    lastname: payload.lastname,
    roles: payload.roles,
  };
}

/**
 * Set the JWT token in an HTTP-only cookie
 */
export async function setAuthCookie(token: string) {
  // In Next.js 15, cookies() is async and needs to be awaited
  const cookieStore = await cookies();
  cookieStore.set("auth_token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // 1 week
  });
}

/**
 * Clear the auth cookie (for logout)
 */
export async function clearAuthCookie() {
  const cookieStore = await cookies();
  cookieStore.delete("auth_token");
}

/**
 * Clear the auth cookie from client side
 */
export function clearAuthCookieClient() {
  // Clear the cookie by setting it to expire in the past
  document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
}
