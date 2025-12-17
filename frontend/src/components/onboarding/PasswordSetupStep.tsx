import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Lock, Loader2, AlertCircle, Check } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import type { StepProps } from './OnboardingWizard';

/**
 * PasswordSetupStep - Step 5 of onboarding wizard
 *
 * Allows new users to create a password before accessing dashboard.
 * This password will be used for future logins.
 *
 * Displays:
 * - Password input field
 * - Confirm password field
 * - Password requirements
 * - "Set Password" button
 *
 * On button click:
 * - Validates password strength and match
 * - Calls apiClient.setPassword()
 * - Proceeds to Step 6 (Completion)
 */
export default function PasswordSetupStep({ onNext, currentState }: StepProps) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Validate password meets requirements
   */
  const validatePassword = (): string | null => {
    if (password.length < 8) {
      return 'Password must be at least 8 characters';
    }

    if (password !== confirmPassword) {
      return 'Passwords do not match';
    }

    return null;
  };

  /**
   * Handle password setup form submission
   */
  const handleSetPassword = async () => {
    setError(null);

    // Validate password
    const validationError = validatePassword();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);

    try {
      // Call API to set password
      await apiClient.setPassword(password);

      // Show success toast
      toast.success('Password created successfully!');

      // Proceed to completion step
      onNext();
    } catch (err: unknown) {
      console.error('Failed to set password:', err);
      const error = err as { response?: { data?: { detail?: string } }; message?: string };

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError('Failed to set password. Please try again.');
      }

      toast.error('Failed to set password');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Check if passwords match (for visual feedback)
   */
  const passwordsMatch = password.length > 0 && confirmPassword.length > 0 && password === confirmPassword;
  const passwordsDoNotMatch = confirmPassword.length > 0 && password !== confirmPassword;

  return (
    <div className="flex flex-col items-center text-center space-y-6 max-w-lg mx-auto">
      {/* Header */}
      <div className="w-full space-y-3">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-gradient-to-br from-primary/20 to-primary/10 p-5 shadow-lg shadow-primary/10">
            <Lock className="h-14 w-14 text-primary" />
          </div>
        </div>
        <h1 className="text-3xl font-bold leading-tight">Create Your Password</h1>
        <p className="text-lg text-muted-foreground">
          Set a password to secure your account and enable future logins
        </p>
      </div>

      {/* Password form */}
      <Card className="w-full shadow-md border-border/50">
        <CardHeader>
          <CardTitle>Choose a Strong Password</CardTitle>
          <CardDescription>
            You'll use this password to log in after completing setup
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Error message */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

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

          {/* Confirm password field */}
          <div className="space-y-2 text-left">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`pl-9 ${passwordsMatch ? 'border-green-500' : ''} ${passwordsDoNotMatch ? 'border-red-500' : ''}`}
                disabled={isLoading}
                required
              />
              {passwordsMatch && (
                <Check className="absolute right-3 top-3 h-4 w-4 text-green-500" />
              )}
            </div>
          </div>

          {/* Password requirements */}
          <div className="text-left space-y-2 pt-2">
            <p className="text-sm font-medium text-muted-foreground">Password requirements:</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li className={`flex items-center gap-2 ${password.length >= 8 ? 'text-green-600' : ''}`}>
                {password.length >= 8 ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <span className="h-4 w-4 flex items-center justify-center">•</span>
                )}
                At least 8 characters
              </li>
              <li className={`flex items-center gap-2 ${passwordsMatch ? 'text-green-600' : ''}`}>
                {passwordsMatch ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <span className="h-4 w-4 flex items-center justify-center">•</span>
                )}
                Passwords match
              </li>
            </ul>
          </div>

          {/* Set password button */}
          <Button
            onClick={handleSetPassword}
            disabled={isLoading || !password || !confirmPassword}
            className="w-full mt-4"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Setting password...
              </>
            ) : (
              'Set Password & Continue'
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Context card */}
      <Card className="w-full border-muted">
        <CardContent className="py-4">
          <p className="text-sm text-muted-foreground text-left">
            <strong className="text-foreground">Why do I need a password?</strong><br />
            After completing onboarding, you'll use your email and this password to log in.
            Your Gmail OAuth connection is separate and remains active.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
