'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import * as StytchJS from '@stytch/vanilla-js';
import { useAuth } from '@/components/auth/AuthProvider';

export default function AuthCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setState } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleAuth = async () => {
      try {
        // Get the token from the URL - this is the raw magic link token
        const token = searchParams.get('token');
        const tokenType = searchParams.get('stytch_token_type');

        if (!token) {
          setError('No authentication token found in URL');
          setLoading(false);
          return;
        }

        // Stytch SDK's AuthenticateResponse type or a simplified version for our needs
        let stytchSDKResponse: any; // Use 'any' for simplicity or define a proper type

        const mockAuthEnabled = process.env.NEXT_PUBLIC_MOCK_AUTH === 'true';
        const mockEmail = searchParams.get('mock_email');

        if (mockAuthEnabled && token === 'mock_auth_token' && mockEmail) {
          console.log('Using mock authentication flow');
          // Simulate Stytch response for mock auth
          stytchSDKResponse = {
            user_id: 'mock_user_id_123',
            user: {
              emails: [{ email: mockEmail, verified: true }],
            },
            session_token: 'mock_session_token',
            session_jwt: 'mock_session_jwt',
            // Add other fields as expected by your downstream logic if necessary
          };
          // No actual Stytch call is made here
        } else {
          // Initialize Stytch client for real authentication
          const stytchClient = new StytchJS.StytchUIClient(process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN || '');
          try {
            stytchSDKResponse = await stytchClient.magicLinks.authenticate(token, {
              session_duration_minutes: 60
            });
          } catch (stytchError: any) {
            console.error('Stytch authentication error:', stytchError);
            throw new Error(stytchError.message || 'Failed to authenticate with Stytch');
          }
        }

        // Use our frontend API route to verify email (avoids CORS issues)
        const userResponse = await fetch('/api/auth/verify-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            // Ensure this path aligns with the structure of stytchSDKResponse (real or mock)
            email: stytchSDKResponse.user?.emails?.[0]?.email || 'fallback_mock@example.com'
          })
        });

        if (!userResponse.ok) {
          const errorText = await userResponse.text();
          console.error('Failed to verify email:', errorText);
          throw new Error('Email verification failed');
        }

        const eligibilityData = await userResponse.json();

        if (!eligibilityData.eligible) {
          throw new Error('Email not eligible for access');
        }

        // Create a user session directly in our provider
        setState({
          isLoading: false,
          isAuthenticated: true,
          user: {
            id: stytchSDKResponse.user_id,
            email: stytchSDKResponse.user?.emails?.[0]?.email || 'fallback_mock@example.com',
            roles: ['member'], // Default role
            firstName: stytchSDKResponse.user?.name?.first_name || '',
            lastName: stytchSDKResponse.user?.name?.last_name || '',
            createdAt: new Date().toISOString(),
            lastLoginAt: new Date().toISOString()
          },
          error: null
        });

        // Redirect to home page on success
        router.push('/');
      } catch (err: any) { // Catch block for the outer try
        console.error('Authentication error in handleAuth:', err);
        setError(err.message || 'Failed to authenticate. Please try again.');
        setLoading(false);
      }
    };

    handleAuth();
  }, [router, searchParams, setState]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h1 className="text-2xl font-bold mb-4">Authenticating...</h1>
        <p>Please wait while we verify your login.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h1 className="text-2xl font-bold mb-4">Authentication Error</h1>
        <p className="text-red-500">{error}</p>
        <button
          onClick={() => router.push('/login')}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Back to Login
        </button>
      </div>
    );
  }

  return null;
}
