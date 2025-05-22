'use client';

import { useState, useEffect } from 'react';

export default function DebugAuth() {
  const [envVars, setEnvVars] = useState<any>({});
  const [cookies, setCookies] = useState<string>('');
  
  useEffect(() => {
    // Get all environment variables that are public
    const publicVars = Object.keys(process.env)
      .filter(key => key.startsWith('NEXT_PUBLIC_'))
      .reduce((obj, key) => {
        return {
          ...obj,
          [key]: process.env[key]
        };
      }, {});
    
    setEnvVars({
      ...publicVars,
      NODE_ENV: process.env.NODE_ENV
    });
    
    // Get cookies
    setCookies(document.cookie);
  }, []);
  
  const handleDevLogin = async () => {
    try {
      const response = await fetch('/api/auth/dev-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: 'jefferyharrell@gmail.com' }),
      });
      
      const data = await response.json();
      
      // Check cookies again
      setCookies(document.cookie);
      
      alert(response.ok ? 'Login successful!' : `Login failed: ${data.message}`);
    } catch (error) {
      console.error('Debug login error:', error);
      alert(`Error: ${(error as any).message}`);
    }
  };
  
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Auth Debug Page</h1>
      
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Environment Variables</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-40">
          {JSON.stringify(envVars, null, 2)}
        </pre>
      </div>
      
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Cookies</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-40">
          {cookies || 'No cookies found'}
        </pre>
      </div>
      
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Actions</h2>
        <button 
          onClick={handleDevLogin}
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded"
        >
          Try Dev Login
        </button>
      </div>
    </div>
  );
}
