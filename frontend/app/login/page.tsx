'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { LogoPlaceholder } from '@/components/LogoPlaceholder';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'email' | 'magic-link'>('email');
  const router = useRouter();

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // TODO: Replace with actual API call to check email eligibility
      const response = await fetch('/api/auth/check-eligibility', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to check email eligibility');
      }
      
      if (data.isEligible) {
        // TODO: Trigger Stytch magic link
        setStep('magic-link');
      } else {
        setError('Access denied');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-6">
            <LogoPlaceholder className="w-16 h-16" />
          </div>
          <CardTitle className="text-2xl font-bold text-center">
            Sign in to Tagline
          </CardTitle>
          <CardDescription className="text-center">
            {step === 'email' 
              ? 'Enter your email to continue' 
              : 'Check your email for a magic link'}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {step === 'email' ? (
            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </div>
              
              {error && (
                <div className="text-sm text-red-500 dark:text-red-400 text-center">
                  {error}
                </div>
              )}
              
              <Button 
                type="submit" 
                className="w-full"
                disabled={isLoading || !email}
              >
                {isLoading ? 'Checking...' : 'Continue with Email'}
              </Button>
            </form>
          ) : (
            <div className="text-center space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                We've sent a magic link to <span className="font-medium">{email}</span>.
                Click the link to sign in.
              </p>
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => setStep('email')}
              >
                Back to sign in
              </Button>
            </div>
          )}
        </CardContent>
        
        <CardFooter className="flex justify-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
