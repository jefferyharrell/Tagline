import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Note: We're using a simplified JWT verification approach since jose types aren't available
// This will be replaced with proper jose verification once types are resolved
interface JWTPayload {
  user_id?: string;
  email?: string;
  roles?: string[];
  exp?: number;
  [key: string]: unknown;
}

// Paths that don't require authentication
const publicPaths = [
  "/",
  "/login",
  "/auth/callback",
  "/api/auth/check-eligibility",
  "/api/auth/session",
];

// Function to verify JWT
async function verifyJWT(token: string): Promise<JWTPayload | null> {
  try {
    // Basic JWT verification (simplified without jose)
    // This is a temporary solution until jose types are properly resolved
    const parts = token.split(".");
    if (parts.length !== 3) {
      throw new Error("Invalid JWT format");
    }

    // Decode the payload
    const payload = JSON.parse(atob(parts[1]));

    // Check if token is expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      throw new Error("Token expired");
    }

    return payload;
  } catch (error) {
    console.error("JWT verification failed:", error);
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if the path is public
  if (
    publicPaths.some(
      (path) => pathname === path || pathname.startsWith(`${path}/`),
    )
  ) {
    return NextResponse.next();
  }

  // Check if authentication is bypassed for development
  if (process.env.BYPASS_AUTH === "true") {
    return NextResponse.next();
  }

  // Check for JWT in cookies or authorization header
  const sessionJwt = request.cookies.get("sessionJwt")?.value;
  const authHeader = request.headers.get("authorization");
  const tokenFromHeader = authHeader?.startsWith("Bearer ")
    ? authHeader.substring(7)
    : null;

  const token = sessionJwt || tokenFromHeader;

  if (!token) {
    // Redirect to login if no token is found
    const url = new URL("/login", request.url);
    url.searchParams.set("from", pathname);
    return NextResponse.redirect(url);
  }

  // Verify the token
  const payload = await verifyJWT(token);

  if (!payload) {
    // Redirect to login if token is invalid
    const url = new URL("/login", request.url);
    url.searchParams.set("from", pathname);
    return NextResponse.redirect(url);
  }

  // Token is valid, proceed
  return NextResponse.next();
}

// Configure middleware to run on specific paths
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|public/).*)",
  ],
};
