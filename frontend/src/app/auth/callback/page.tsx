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
        // Initialize Stytch client
        const stytchClient = new StytchJS.StytchUIClient(process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN || '');
        
        // Get the token from the URL
        const token = searchParams.get('token');
        
        if (!token) {
          setError('No authentication token found in URL');
          setLoading(false);
          return;
        }
        
        // Authenticate with Stytch using a shorter session duration to avoid the error
        // Using a shorter duration to avoid the invalid_session_duration error
        const response = await stytchClient.magicLinks.authenticate(token, {
          session_duration_minutes: 1440 // 1 day in minutes (instead of default 30 days)
        });
        
        // Log detailed information about the Stytch response
        console.log('Authentication successful');
        console.log('Session token:', response.session_token);
        console.log('Session JWT:', response.session_jwt);
        console.log('User ID:', response.user_id);
        
        // Get the session token
        const sessionToken = response.session_token;
        
        // Fetch user data from our API using the session token
        const userResponse = await fetch('/api/auth/session', {
          headers: {
            Authorization: `Bearer ${sessionToken}`
          }
        });
        
        if (userResponse.ok) {
          const userData = await userResponse.json();
          
          // Update the auth state in our provider
          setState({
            isLoading: false,
            isAuthenticated: true,
            user: userData.user,
            error: null
          });
          
          // Redirect to dashboard on success
          router.push('/dashboard');
        } else {
          throw new Error('Failed to fetch user data');
        }
      } catch (err) {
        console.error('Authentication error:', err);
        setError('Failed to authenticate. Please try again.');
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
