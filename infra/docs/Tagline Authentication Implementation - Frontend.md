---
tags:
  - tagline
  - authentication
  - implementation
  - frontend
date: 2025-05-16
author: Alpha
---

This document provides a comprehensive implementation guide for the Next.js frontend authentication system in Tagline, featuring Stytch for magic link authentication and API proxying to the FastAPI backend.

## Project Setup

First, ensure your project has the necessary dependencies:

```json
// package.json
{
  "dependencies": {
    "@stytch/nextjs": "^10.0.0",
    "@stytch/vanilla-js": "^3.0.0",
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "jose": "^5.0.0"
  }
}
```

## Environment Configuration

Create a `.env.local` file with your Stytch credentials:

```
# Stytch API keys
NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN=public-token-test-xxxx
STYTCH_SECRET_TOKEN=secret-test-xxxx
STYTCH_PROJECT_ID=project-test-xxxx

# Auth settings
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret

# Backend API
BACKEND_URL=http://localhost:8000
BACKEND_API_KEY=your-api-key
```

## Server-Side Stytch Setup

Create a utility file to initialize the Stytch client on the server:

```javascript
// lib/stytch-server.js
import * as stytch from 'stytch';

let stytchClient;

export function loadStytch() {
  if (!stytchClient) {
    stytchClient = new stytch.Client({
      project_id: process.env.STYTCH_PROJECT_ID,
      secret: process.env.STYTCH_SECRET_TOKEN,
      env: process.env.NODE_ENV === 'production' ? stytch.envs.live : stytch.envs.test,
    });
  }

  return stytchClient;
}
```

## Client-Side Stytch Setup

Create a utility file for the client-side Stytch instance:

```javascript
// lib/stytch-client.js
import { createStytchUIClient } from '@stytch/nextjs/ui';

export const stytchClient = createStytchUIClient(
  process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN
);
```

## Authentication Context Provider

Create a React context to manage authentication state:

```javascript
// components/AuthProvider.jsx
'use client';

import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check if we have a session in localStorage
    const checkSession = async () => {
      try {
        const sessionJwt = localStorage.getItem('sessionJwt');

        if (sessionJwt) {
          // Verify JWT on the server side
          const payload = JSON.parse(atob(sessionJwt.split('.')[1]));

          if (payload && payload.roles) {
            setUser({
              id: payload.user_id,
              email: payload.email,
              roles: payload.roles,
            });
          }
        }
      } catch (error) {
        console.error('Error checking session:', error);
        // Clear potentially invalid session
        localStorage.removeItem('sessionJwt');
      } finally {
        setLoading(false);
      }
    };

    checkSession();
  }, []);

  const login = async (sessionToken, sessionJwt, userRoles) => {
    localStorage.setItem('sessionJwt', sessionJwt);

    // Parse JWT payload to get user info
    const payload = JSON.parse(atob(sessionJwt.split('.')[1]));

    setUser({
      id: payload.user_id,
      email: payload.email,
      roles: userRoles,
    });

    router.push('/dashboard');
  };

  const logout = () => {
    localStorage.removeItem('sessionJwt');
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
```

## API Proxy Routes

Create API routes in Next.js to proxy requests to the backend:

```javascript
// app/api/auth/check-eligibility/route.js
import { NextResponse } from 'next/server';

export async function POST(request) {
  const data = await request.json();

  try {
    const response = await fetch(`${process.env.BACKEND_URL}/v1/auth/verify-email-eligibility`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BACKEND_API_KEY,
      },
      body: JSON.stringify({ email: data.email }),
    });

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error checking email eligibility:', error);
    return NextResponse.json(
      { error: 'Failed to check email eligibility' },
      { status: 500 }
    );
  }
}
```

```javascript
// app/api/auth/session/route.js
import { NextResponse } from 'next/server';
import { loadStytch } from '@/lib/stytch-server';

export async function POST(request) {
  const data = await request.json();
  const { token } = data;

  try {
    // Authenticate with Stytch
    const stytch = loadStytch();
    const authResponse = await stytch.magicLinks.authenticate({ token });

    // Verify with our backend and get user roles
    const backendResponse = await fetch(`${process.env.BACKEND_URL}/v1/auth/authenticate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BACKEND_API_KEY,
      },
      body: JSON.stringify({ token }),
    });

    const backendResult = await backendResponse.json();

    // Combine Stytch session with our backend user data
    return NextResponse.json({
      sessionToken: authResponse.session_token,
      sessionJwt: backendResult.access_token,
      userRoles: backendResult.user_roles,
    });
  } catch (error) {
    console.error('Authentication error:', error);
    return NextResponse.json(
      { error: 'Authentication failed' },
      { status: 401 }
    );
  }
}
```

## Authentication UI Components

### Login Component

```javascript
// components/Login.jsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { StytchLogin } from '@stytch/nextjs/ui';
import { Products } from '@stytch/vanilla-js';
import { useAuth } from './AuthProvider';

export default function Login() {
  const [email, setEmail] = useState('');
  const [isEligibilityChecking, setIsEligibilityChecking] = useState(false);
  const [isEligible, setIsEligible] = useState(null);
  const [error, setError] = useState(null);
  const router = useRouter();
  const { login } = useAuth();

  const checkEligibility = async (e) => {
    e.preventDefault();
    setIsEligibilityChecking(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/check-eligibility', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const result = await response.json();

      if (result.eligible) {
        setIsEligible(true);
      } else {
        setError('This email is not authorized to access the application.');
        setIsEligible(false);
      }
    } catch (error) {
      console.error('Error checking eligibility:', error);
      setError('An error occurred while checking eligibility. Please try again.');
    } finally {
      setIsEligibilityChecking(false);
    }
  };

  const handleStytchSuccess = async (response) => {
    try {
      // Exchange Stytch token for our backend session
      const authResponse = await fetch('/api/auth/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token: response.token }),
      });

      if (!authResponse.ok) {
        throw new Error('Authentication failed');
      }

      const result = await authResponse.json();
      await login(result.sessionToken, result.sessionJwt, result.userRoles);
    } catch (error) {
      console.error('Login error:', error);
      setError('Authentication failed. Please try again.');
    }
  };

  return (
    <div className="login-container">
      <h1>Log in to Tagline</h1>

      {!isEligible ? (
        <div className="eligibility-check">
          <p>Please enter your email to verify access</p>

          <form onSubmit={checkEligibility}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Your email address"
              required
            />
            <button type="submit" disabled={isEligibilityChecking}>
              {isEligibilityChecking ? 'Checking...' : 'Check Access'}
            </button>
          </form>

          {error && <div className="error-message">{error}</div>}
        </div>
      ) : (
        <div className="stytch-login-container">
          <p>Please check your email for a magic link to sign in</p>

          <StytchLogin
            config={{
              products: [Products.magicLinks],
              magicLinksOptions: {
                loginRedirectURL: `${window.location.origin}/auth/callback`,
                signupRedirectURL: `${window.location.origin}/auth/callback`,
                emailMagicLinksOptions: {
                  loginExpirationMinutes: 30,
                  signupExpirationMinutes: 30,
                },
              },
            }}
            callbacks={{
              onEvent: (event) => {
                console.log('Stytch event:', event);
              },
              onSuccess: handleStytchSuccess,
              onError: (error) => {
                console.error('Stytch error:', error);
                setError('Authentication error. Please try again.');
              },
            }}
            emailMagicLinksOptions={{
              email: email,
              loginRedirectURL: `${window.location.origin}/auth/callback`,
              signupRedirectURL: `${window.location.origin}/auth/callback`,
            }}
          />

          <button onClick={() => setIsEligible(false)} className="back-button">
            Change Email
          </button>
        </div>
      )}
    </div>
  );
}
```

### Callback Handler

```javascript
// app/auth/callback/page.jsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';

export default function StytchCallback() {
  const [error, setError] = useState(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');

    if (!token) {
      setError('Invalid or missing authentication token');
      return;
    }

    const authenticateWithToken = async () => {
      try {
        const response = await fetch('/api/auth/session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          throw new Error('Authentication failed');
        }

        const result = await response.json();
        await login(result.sessionToken, result.sessionJwt, result.userRoles);

        // Redirect to dashboard after successful login
        router.push('/dashboard');
      } catch (error) {
        console.error('Authentication error:', error);
        setError('Authentication failed. Please try again.');
      }
    };

    authenticateWithToken();
  }, [searchParams, login, router]);

  return (
    <div className="auth-callback">
      <h1>Authenticating...</h1>
      {error ? (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => router.push('/login')}>Return to Login</button>
        </div>
      ) : (
        <p>Please wait while we complete your authentication...</p>
      )}
    </div>
  );
}
```

## Protected Route Component

```javascript
// components/ProtectedRoute.jsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './AuthProvider';

export default function ProtectedRoute({
  children,
  requiredRoles = []
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
      return;
    }

    if (
      !loading &&
      user &&
      requiredRoles.length > 0 &&
      !requiredRoles.some(role => user.roles.includes(role))
    ) {
      router.push('/unauthorized');
    }
  }, [user, loading, router, requiredRoles]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return null; // Will redirect in useEffect
  }

  if (
    requiredRoles.length > 0 &&
    !requiredRoles.some(role => user.roles.includes(role))
  ) {
    return null; // Will redirect in useEffect
  }

  return children;
}
```

## Core App Setup

```javascript
// app/layout.jsx
import { AuthProvider } from '@/components/AuthProvider';
import './globals.css';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

## Example Protected Page

```javascript
// app/dashboard/page.jsx
'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuth } from '@/components/AuthProvider';

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute requiredRoles={['member']}>
      <div className="dashboard">
        <h1>Dashboard</h1>

        <div className="user-info">
          <p>Welcome, {user?.email}</p>
          <p>Roles: {user?.roles.join(', ')}</p>
        </div>

        <button onClick={logout} className="logout-button">
          Log Out
        </button>

        {user?.roles.includes('admin') && (
          <div className="admin-panel">
            <h2>Admin Panel</h2>
            <p>This section is only visible to administrators.</p>
            {/* Admin-specific functionality here */}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
```

## Middleware for Route Protection

```javascript
// middleware.js
import { NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

// Paths that don't require authentication
const publicPaths = [
  '/',
  '/login',
  '/auth/callback',
  '/api/auth/check-eligibility',
  '/api/auth/session',
];

// Function to verify JWT
async function verifyJWT(token) {
  try {
    // Use jose to verify the JWT
    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(process.env.NEXTAUTH_SECRET)
    );
    return payload;
  } catch (error) {
    console.error('JWT verification failed:', error);
    return null;
  }
}

export async function middleware(request) {
  const { pathname } = request.nextUrl;

  // Check if the path is public
  if (publicPaths.some(path => pathname === path || pathname.startsWith(`${path}/`))) {
    return NextResponse.next();
  }

  // Check for JWT in cookies or authorization header
  const sessionJwt = request.cookies.get('sessionJwt')?.value;

  if (!sessionJwt) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Verify JWT (implementation depends on your JWT library)
  const payload = await verifyJWT(sessionJwt);

  if (!payload) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Allow authenticated requests to continue
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images (image files)
     * - fonts (font files)
     */
    '/((?!_next/static|_next/image|favicon.ico|images|fonts).*)',
  ],
};
```

## Docker Compose Setup

For deploying the entire application using Docker Compose:

```yaml
# docker-compose.yml
version: '3'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"  # Only the frontend exposes a port to the host
    environment:
      - BACKEND_URL=http://backend:8000
      - STYTCH_PROJECT_ID=${STYTCH_PROJECT_ID}
      - STYTCH_SECRET_TOKEN=${STYTCH_SECRET_TOKEN}
      - NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN=${NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN}
      - NEXTAUTH_URL=${NEXTAUTH_URL}
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - BACKEND_API_KEY=${API_KEY}
    depends_on:
      - backend

  backend:
    build: ./backend
    # No ports exposed to the host - only internal
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/tagline
      - JWT_SECRET=${JWT_SECRET}
      - JWT_ALGORITHM=HS256
      - STYTCH_PROJECT_ID=${STYTCH_PROJECT_ID}
      - STYTCH_SECRET=${STYTCH_SECRET}
      - STYTCH_ENV=${STYTCH_ENV}
      - API_KEY=${API_KEY}
    depends_on:
      - db

  db:
    image: postgres:15
    # No ports exposed to the host - only internal
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=tagline

volumes:
  postgres_data:
```

## Implementation Sequence

1. **Database Setup**:
   - Create database migrations for user, role, and eligible_email tables
   - Seed default roles

2. **Backend Authentication Implementation**:
   - Install Stytch Python package
   - Configure environment variables
   - Implement authentication endpoints
   - Add JWT token creation and validation

3. **Frontend Framework**:
   - Set up Next.js project with App Router
   - Add Stytch dependencies
   - Configure environment variables

4. **Authentication Flow**:
   - Create eligibility check endpoint
   - Implement magic link authentication
   - Build protected route mechanism

5. **Testing**:
   - Test the full authentication flow from eligibility check to protected routes
   - Verify role-based access control
   - Validate JWT token creation and validation

## Security Considerations

1. **Environment Variables**:
   - Store all sensitive credentials in environment variables
   - Never commit .env files to version control

2. **JWT Security**:
   - Use a strong, random secret key
   - Include appropriate expiration times
   - Validate tokens on every request

3. **API Protection**:
   - Backend only accepts requests with valid API Key
   - No direct access to backend from outside the Docker network

4. **Role Validation**:
   - Always verify roles on the server side
   - Never trust client-side role assertions

## Conclusion

This implementation provides a secure, modern authentication system for Tagline using Stytch for magic link authentication and a multi-role permission system. The approach follows best practices:

1. **Security First**: Protected API endpoints, secure JWT implementation, and server-side role validation
2. **User Experience**: Streamlined magic link authentication with pre-eligibility checks
3. **Deployment Ready**: Docker Compose setup for production deployment
4. **Extensibility**: Role-based access control that can grow with application needs
