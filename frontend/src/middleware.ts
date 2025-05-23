import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getJwtToken } from "./lib/jwt-utils";

// Paths that don't require authentication
const publicPaths = [
  "/",
  "/login",
  "/authenticate",
  "/api/auth/callback",
  "/api/auth/check-email",
  "/debug-auth",
  "/api/auth/dev-login",
];

// Stytch magic link redirect pattern
const STYTCH_REDIRECT_PATTERN = /test\.stytch\.com\/v1\/magic_links\/redirect/;

// Check if the path is public
function isPublicPath(path: string): boolean {
  // Allow Stytch redirect URLs
  if (STYTCH_REDIRECT_PATTERN.test(path)) {
    return true;
  }

  return publicPaths.some(
    (publicPath) =>
      path === publicPath ||
      path.startsWith(`${publicPath}/`) ||
      path.startsWith("/_next/") ||
      path.startsWith("/images/") ||
      path.startsWith("/fonts/") ||
      path.includes("favicon.ico"),
  );
}

// Function to verify JWT
async function verifyJWT(token: string) {
  try {
    // Dynamically import jose to avoid build issues
    const { jwtVerify } = await import("jose");

    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(process.env.JWT_SECRET || ""),
    );

    return payload;
  } catch (error) {
    console.error("JWT verification failed:", error);
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (isPublicPath(pathname) || isPublicPath(request.url)) {
    return NextResponse.next();
  }

  // Check for JWT token
  const token = getJwtToken(request);

  if (!token) {
    // Redirect to root path (where login form is) if no token
    const loginUrl = new URL("/", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Verify JWT token
  const payload = await verifyJWT(token);

  if (!payload) {
    // Redirect to root path (where login form is) if token is invalid
    const loginUrl = new URL("/", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Check for role-specific routes
  const userRoles = (payload as { roles?: string[] }).roles || [];
  if (pathname.startsWith("/admin") && !userRoles.includes("admin")) {
    // Redirect to unauthorized page if user doesn't have admin role
    return NextResponse.redirect(new URL("/unauthorized", request.url));
  }

  // Allow authenticated requests to continue
  return NextResponse.next();
}

// Configure which routes use this middleware
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
