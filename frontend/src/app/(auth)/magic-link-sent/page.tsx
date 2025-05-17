'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function MagicLinkSent() {
  const [email, setEmail] = useState<string>('your email');

  useEffect(() => {
    // Get email from session storage on client side
    if (typeof window !== 'undefined') {
      const storedEmail = sessionStorage.getItem('auth:email');
      if (storedEmail) {
        setEmail(storedEmail);
        // Clear the email from session storage after reading
        sessionStorage.removeItem('auth:email');
      }
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-jlla-white py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 text-center">
        <div>
          <h2 className="text-3xl font-bold text-jlla-black">
            Check your email
          </h2>
          <p className="mt-2 text-sm text-jlla-black/80">
            We've sent a magic link to <span className="font-medium text-jlla-red">{email}</span>
          </p>
        </div>

        <div className="mt-8 bg-white py-8 px-4 shadow-lg sm:rounded-lg border border-gray-100">
          <div className="text-sm text-jlla-black/80">
            <p>Click the link in the email to sign in to your account.</p>
            <p className="mt-2">
              Didn't receive an email?{' '}
              <Link 
                href="/login" 
                className="font-medium text-jlla-red hover:text-jlla-red/80 transition-colors"
              >
                Try again
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
