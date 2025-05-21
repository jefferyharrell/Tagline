'use client';

import { useStytch } from '@stytch/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function LoginPage() {
  const stytch = useStytch();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    // Check for existing authentication
    const checkAuth = async () => {
      try {
        const session = await stytch.session.getSync();
        if (session) {
          router.push('/dashboard');
        }
      } catch (error) {
        console.error('Error checking session:', error);
      }
    };

    checkAuth();
  }, [stytch, router]);

  const checkEmailEligibility = async (email: string): Promise<{ isEligible: boolean; error?: string }> => {
    try {
      const response = await fetch('/api/auth/check-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const error = await response.json();
        return {
          isEligible: false,
          error: error.error || 'Failed to check email eligibility'
        };
      }

      const data = await response.json();
      return { isEligible: data.eligible };
    } catch (error) {
      console.error('Error checking email eligibility:', error);
      return {
        isEligible: false,
        error: 'Failed to check email eligibility. Please try again.'
      };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setMessage('');

    try {
      // First check if email is eligible
      const { isEligible, error } = await checkEmailEligibility(email);

      if (!isEligible) {
        setMessage(error || 'This email is not authorized to access the application.');
        setIsSuccess(false);
        return;
      }

      // If email is eligible, proceed with magic link
      await stytch.magicLinks.email.loginOrCreate(email, {
        login_magic_link_url: `${process.env.NEXT_PUBLIC_APP_URL}/authenticate`,
        signup_magic_link_url: `${process.env.NEXT_PUBLIC_APP_URL}/authenticate`,
        login_expiration_minutes: 10,
        signup_expiration_minutes: 10,
      });

      setMessage('Check your email for a magic link to sign in.');
      setIsSuccess(true);
    } catch (error) {
      console.error('Error sending magic link:', error);
      setMessage('Failed to send magic link. Please try again.');
      setIsSuccess(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter your email to receive a magic link
          </p>
        </div>

        {message && (
          <div className={`mt-4 p-4 rounded-md ${isSuccess ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {message}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email-address" className="sr-only">
                Email address
              </label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                disabled={isLoading}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !email}
              className={`group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white ${
                isLoading || !email
                  ? 'bg-indigo-300'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500`}
            >
              {isLoading ? 'Sending...' : 'Send Magic Link'}
            </button>
          </div>
          
          {/* Dev Login Button - Only visible in development with bypass enabled */}
          {process.env.NODE_ENV !== 'production' && process.env.NEXT_PUBLIC_AUTH_BYPASS_ENABLED === 'true' && (
            <div className="mt-4">
              <button
                type="button"
                onClick={async () => {
                  
                  try {
                    setIsLoading(true);
                    const devEmail = email || process.env.NEXT_PUBLIC_AUTH_BYPASS_DEFAULT_EMAIL || '';
                    
                    if (!devEmail) {
                      setMessage('Please enter an email address for dev login');
                      setIsSuccess(false);
                      setIsLoading(false);
                      return;
                    }
                    
                    const response = await fetch('/api/auth/dev-login', {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify({ email: devEmail }),
                    });
                    
                    if (!response.ok) {
                      const error = await response.json();
                      throw new Error(error.message || 'Development login failed');
                    }
                    
                    // Redirect to dashboard
                    router.push('/dashboard');
                  } catch (error) {
                    console.error('Dev login error:', error);
                    setMessage((error as Error).message || 'Development login failed');
                    setIsSuccess(false);
                  } finally {
                    setIsLoading(false);
                  }
                }}
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                ⚙️ Developer Login
              </button>
              <div className="mt-1 text-xs text-center text-gray-500">
                Bypasses email verification in development environment
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
