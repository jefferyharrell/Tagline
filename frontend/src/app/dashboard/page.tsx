import React from 'react';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function Dashboard() {
  // In a real implementation, we would verify the JWT and get user data
  // For now, we'll just check if the auth_token cookie exists
  const cookieStore = await cookies();
  const authToken = cookieStore.get('auth_token');

  if (!authToken) {
    redirect('/');
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-center mb-6">Tagline Dashboard</h1>
        <p className="text-center text-gray-600 mb-8">
          Welcome to the Tagline media management system for the Junior League of Los Angeles.
        </p>
        <div className="flex justify-center">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-700">
            <p>You are successfully logged in!</p>
            <p className="mt-2">This is a temporary dashboard page. The full interface will be implemented soon.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
