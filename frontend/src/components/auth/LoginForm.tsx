'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mail, Lock, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { setToken } from '@/lib/auth';

/**
 * Login form component
 *
 * Allows existing users to sign in with email and password.
 * After successful login, redirects to dashboard.
 */
export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle login form submission
   */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Validate inputs
      if (!email || !password) {
        setError('Please enter both email and password');
        setIsLoading(false);
        return;
      }

      // Call login API
      const response = await apiClient.login(email, password);

      // Backend returns token directly without {data: {...}} wrapper
      // Type cast to handle mismatch between backend response and ApiResponse type
      const access_token = (response as any).access_token || (response as any).data?.access_token;

      if (access_token) {
        // Store JWT token
        setToken(access_token);

        // Show success toast
        toast.success('Logged in successfully!');

        // Redirect to dashboard
        router.push('/dashboard');
      } else {
        throw new Error('Invalid login response');
      }
    } catch (err: unknown) {
      console.error('Login failed:', err);

      // Handle different error types
      const error = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };

      if (error.response?.status === 401) {
        setError('Incorrect email or password');
      } else if (error.response?.status === 429) {
        setError('Too many login attempts. Please try again later.');
      } else if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError('Login failed. Please try again.');
      }

      toast.error('Login failed');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center text-center space-y-6 max-w-md mx-auto">
      {/* Login header */}
      <div className="w-full space-y-3">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-gradient-to-br from-primary/20 to-primary/10 p-5 shadow-lg shadow-primary/10">
            <Lock className="h-14 w-14 text-primary" />
          </div>
        </div>
        <h1 className="text-3xl font-bold leading-tight">Welcome Back</h1>
        <p className="text-lg text-muted-foreground">
          Sign in to access your Mail Agent dashboard
        </p>
      </div>

      {/* Login form card */}
      <Card className="w-full shadow-md border-border/50">
        <CardHeader className="space-y-2">
          <CardTitle className="text-2xl">Sign In</CardTitle>
          <CardDescription className="text-base">
            Enter your credentials to continue
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error message */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Email field */}
            <div className="space-y-2 text-left">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                  disabled={isLoading}
                  required
                />
              </div>
            </div>

            {/* Password field */}
            <div className="space-y-2 text-left">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  disabled={isLoading}
                  required
                />
              </div>
            </div>

            {/* Submit button */}
            <Button
              type="submit"
              className="w-full mt-6"
              size="lg"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Link to onboarding for new users */}
      <Card className="w-full border-muted">
        <CardContent className="py-4">
          <p className="text-sm text-muted-foreground">
            <strong className="text-foreground">New to Mail Agent?</strong><br />
            First-time users need to complete the onboarding process to connect services and set up their account.{' '}
            <a href="/onboarding" className="text-primary hover:underline font-medium">
              Get started
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
