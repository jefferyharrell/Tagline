'use client';

import { useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { useRouter } from 'next/navigation'; 

export default function LoginPage() {
  const auth = useAuth();
  const { checkEligibility } = auth;
  const [email, setEmail] = useState('');
  const [isChecking, setIsChecking] = useState(false);
  const [isEligible, setIsEligible] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter(); 

  const mockAuthEnabled = process.env.NEXT_PUBLIC_MOCK_AUTH === 'true';

  const handleEligibilityCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setIsChecking(true);
    setError(null);

    try {
      const eligible = await checkEligibility(email);
      setIsEligible(eligible);
      
      if (!eligible) {
        setError('This email is not eligible for access. Please contact an administrator if you believe this is an error.');
      }
    } catch (err) {
      setError('Failed to check eligibility. Please try again.');
      console.error('Eligibility check error:', err);
    } finally {
      setIsChecking(false);
    }
  };

  const handleMockLogin = () => {
    const mockEmail = email || 'mockuser@example.com'; 
    const mockAuthUrl = `/auth/callback?token=mock_auth_token&stytch_token_type=mock_magic_links&mock_email=${encodeURIComponent(mockEmail)}`;
    router.push(mockAuthUrl);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to Tagline
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Junior League of Los Angeles Media Library
          </p>
        </div>

        {!isEligible ? (
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
                      className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      placeholder="your.email@example.com"
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
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {isChecking ? 'Checking...' : 'Check Eligibility'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : (
          <div className="mt-8">
            <div className="rounded-md shadow-sm">
              <div className="p-4 border border-gray-300 rounded-md">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Sign in with Magic Link</h3>
                <p className="text-sm text-gray-600 mb-4">
                  A magic link will be sent to {email}. Click the link in your email to sign in.  
                </p>
                <button
                  onClick={() => auth.login(email)}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Send Magic Link
                </button>
              </div>
            </div>
          </div>
        )}

        {mockAuthEnabled && (
          <div className="mt-4">
            <button
              onClick={handleMockLogin}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
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
