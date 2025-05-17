'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AuthCallbackPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const token = searchParams.get('token');
        const error = searchParams.get('error');

        if (error) {
          throw new Error(error);
        }

        if (!token) {
          throw new Error('No authentication token provided');
        }

        // Exchange the Stytch token for a session
        const response = await fetch('/api/auth/session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.message || 'Failed to authenticate. Please try again.'
          );
        }
        
        const { sessionToken, user } = await response.json();
        
        // Store the session token (this would typically be handled by your auth provider)
        // For now, we'll just log it and redirect
        console.log('Session established for user:', user);
        
        // Redirect to dashboard or the originally requested page
        const redirectTo = searchParams.get('redirectTo') || '/dashboard';
        router.push(redirectTo);
        
      } catch (err) {
        console.error('Authentication error:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    handleCallback();
  }, [router, searchParams]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
          <p className="text-lg font-medium">Completing sign in...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
        <div className="w-full max-w-md p-6 space-y-4 bg-white dark:bg-gray-800 rounded-lg shadow-md">
          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-bold">Sign In Failed</h1>
            <p className="text-gray-600 dark:text-gray-400">{error}</p>
          </div>
          <div className="pt-4">
            <Button 
              className="w-full" 
              onClick={() => router.push('/login')}
            >
              Return to Login
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
