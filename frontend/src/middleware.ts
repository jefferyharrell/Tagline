import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Define public paths that don't require authentication
const publicPaths = [
  '/',
  '/login',
  '/auth/callback',
  '/api/auth/check-eligibility',
  '/api/auth/verify-email'
];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Check if the path is public
  if (publicPaths.some(path => pathname === path || pathname.startsWith(`${path}/`))) {
    return NextResponse.next();
  }
  
  // Check if the path is an API route
  if (pathname.startsWith('/api/')) {
    // For API routes, check the Authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }
    
    // Let the API route handle token validation
    return NextResponse.next();
  }
  
  // For non-API routes, check for session cookie
  const sessionToken = request.cookies.get('stytch_session')?.value;
  
  if (!sessionToken) {
    // Redirect to login if no session token
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  try {
    // Instead of directly authenticating with Stytch here,
    // we'll just check if the session token exists and let the API route handle validation
    // This simplifies our middleware and avoids direct Stytch dependency
    
    // Session token exists, continue to the route which will validate it
    return NextResponse.next();
  } catch (error) {
    console.error('Middleware authentication error:', error);
    
    // Clear the invalid cookie
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('stytch_session');
    
    return response;
  }
}

// Configure the middleware to run on specific paths
export const config = {
  matcher: [
    // Match all paths except for static files, favicon, etc.
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
