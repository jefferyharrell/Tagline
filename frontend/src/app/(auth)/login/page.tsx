'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { useRouter } from 'next/navigation'; 

export default function LoginPage() {
  const auth = useAuth();
  const { checkEligibility } = auth;
  const [email, setEmail] = useState('');
  const [isChecking, setIsChecking] = useState(false);
  const [isEligible, setIsEligible] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const router = useRouter(); 

  const mockAuthEnabled = process.env.NEXT_PUBLIC_MOCK_AUTH === 'true';
  
  // Auto-redirect to magic link sent page after a delay
  useEffect(() => {
    if (emailSent) {
      const redirectTimer = setTimeout(() => {
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('auth:email', email);
        }
        router.push('/magic-link-sent');
      }, 1500); // 1.5 second delay before redirecting
      
      return () => clearTimeout(redirectTimer);
    }
  }, [emailSent, email, router]);

  const handleEligibilityCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setIsChecking(true);
    setError(null);

    try {
      // If mock auth is enabled, use the mock login flow immediately
      if (mockAuthEnabled) {
        handleMockLogin();
        return;
      }
      
      // Check eligibility first
      const eligible = await checkEligibility(email);
      
      if (!eligible) {
        setError('This email is not eligible for access. Please contact an administrator if you believe this is an error.');
        setIsEligible(false);
        setIsChecking(false);
        return;
      }
      
      // Show email sent status immediately
      setEmailSent(true);
      
      // Process the login in the background
      auth.login(email).catch(err => {
        console.error('Login error:', err);
        // If there's an error, we'll handle it silently since the user already sees the success message
        // In a production app, you might want to log this to a monitoring service
      });
      
      // The useEffect will handle the redirect after a short delay
      
    } catch (err) {
      setError('Failed to process your request. Please try again.');
      console.error('Login error:', err);
      setIsChecking(false);
      setEmailSent(false);
    }
  };

  const handleMockLogin = () => {
    const mockEmail = email || 'mockuser@example.com'; 
    const mockAuthUrl = `/auth/callback?token=mock_auth_token&stytch_token_type=mock_magic_links&mock_email=${encodeURIComponent(mockEmail)}`;
    router.push(mockAuthUrl);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-jlla-white py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold text-jlla-black">
            Sign in to Tagline
          </h2>
          <p className="mt-2 text-center text-sm text-jlla-black/80">
            Junior League of Los Angeles Media Library
          </p>
        </div>

        {emailSent ? (
          <div className="mt-8 text-center">
            <div className="rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">Email sent!</h3>
                  <div className="mt-2 text-sm text-green-700">
                    <p>Check your inbox for a magic link to sign in.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : !isEligible ? (
          <div className="mt-8">
            <div className="rounded-md shadow-sm">
              <form onSubmit={handleEligibilityCheck} className="space-y-6">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email address
                  </label>
                  <div className="mt-1">
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-jlla-red focus:border-jlla-red sm:text-sm"
                      placeholder="your.email@example.com"
                      disabled={isChecking}
                    />
                  </div>
                </div>

                {error && (
                  <div className="text-red-500 text-sm mt-1">{error}</div>
                )}

                <div>
                  <button
                    type="submit"
                    disabled={isChecking}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#d32a40] hover:bg-[#d32a40]/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#d32a40]/80 disabled:opacity-50 transition-colors"
                  >
                    {isChecking ? 'Sending...' : 'Sign in'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : null}

        {mockAuthEnabled && (
          <div className="mt-4">
            <button
              onClick={handleMockLogin}
              className="w-full flex justify-center py-2 px-4 border border-jlla-black/20 rounded-md shadow-sm text-sm font-medium text-jlla-black bg-jlla-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-jlla-red/50 transition-colors"
            >
              Mock Login (Dev Only)
            </button>
            <p className="mt-2 text-center text-xs text-gray-500">
              (Uses '{email || 'mockuser@example.com'}')
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
