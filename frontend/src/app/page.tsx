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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setMessage('');

    try {
      // Start the magic link flow
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
        </form>
      </div>
    </div>
  );
}
