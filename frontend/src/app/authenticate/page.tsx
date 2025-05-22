'use client';

import { useStytch } from '@stytch/nextjs';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function AuthenticatePage() {
  const stytch = useStytch();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authenticateWithToken = async () => {
      try {
        // Get token and type from URL params
        const token = searchParams.get('token');
        const tokenType = searchParams.get('stytch_token_type');
        
        
        if (!token) {
          setError('No authentication token found');
          setIsLoading(false);
          return;
        }

        
        // Send token to our backend API
        const response = await fetch('/api/auth/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.message || `Authentication failed with status ${response.status}`);
        }

        const authData = await response.json();
        
        // Redirect to dashboard on success
        router.push('/dashboard');
      } catch (error) {
        console.error('Authentication error:', error);
        setError((error as Error).message || 'Authentication failed');
        setIsLoading(false);
      }
    };

    authenticateWithToken();
  }, [stytch, router, searchParams]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-4">Authenticating...</h1>
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-semibold text-red-600 mb-4">Authentication Error</h1>
          <p className="text-gray-700 mb-4">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  return null;
}
