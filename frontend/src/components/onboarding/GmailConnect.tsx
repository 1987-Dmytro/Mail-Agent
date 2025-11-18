'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Check, Loader2, Mail, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { setToken } from '@/lib/auth';
import { useAuthStatus } from '@/hooks/useAuthStatus';

/**
 * OAuth flow states
 */
type OAuthState = 'initial' | 'loading' | 'success' | 'error';

/**
 * Error types for better error messaging
 */
type ErrorType =
  | 'config_fetch_failed'
  | 'user_denied'
  | 'invalid_state'
  | 'callback_failed'
  | 'network_error'
  | 'unknown';

interface GmailConnectProps {
  /**
   * Callback after successful OAuth connection
   */
  onSuccess?: () => void;
  /**
   * Callback after OAuth error
   */
  onError?: (error: string) => void;
  /**
   * Callback for navigation after connection
   * Used by onboarding wizard to advance to next step
   */
  onNavigate?: () => void;
}

/**
 * Gmail OAuth Connection Component
 *
 * Handles the complete OAuth 2.0 authorization code grant flow:
 * 1. Fetch OAuth config from backend
 * 2. Generate CSRF state token and redirect to Google
 * 3. Handle OAuth callback with authorization code
 * 4. Exchange code for JWT token
 * 5. Store token and show success state
 *
 * Security features:
 * - CSRF protection via state parameter
 * - State token stored in sessionStorage (temporary)
 * - JWT token stored in localStorage (persistent)
 * - Input validation on callback params
 */
export function GmailConnect({ onSuccess, onError, onNavigate }: GmailConnectProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Check authentication status on mount for persistence (AC: 6)
  const { isAuthenticated, isLoading: authLoading, user: authUser } = useAuthStatus();

  const [state, setState] = useState<OAuthState>('initial');
  const [errorType, setErrorType] = useState<ErrorType | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [userEmail, setUserEmail] = useState<string>('');
  const [authUrl, setAuthUrl] = useState<string>('');

  /**
   * Check if user is already authenticated on mount
   * If authenticated, skip OAuth flow and show success state immediately (AC: 6)
   */
  useEffect(() => {
    // CRITICAL FIX: Check token directly from localStorage FIRST
    const token = localStorage.getItem('auth_token');
    if (token && state === 'initial') {
      console.log('Token found in localStorage, showing success state');
      setState('success');

      // Try to get email from API or fallback to localStorage
      if (isAuthenticated && authUser?.gmail_connected) {
        setUserEmail(authUser.email);
      }

      // Call onSuccess to update wizard state
      if (onSuccess) {
        onSuccess();
      }
      return;
    }

    if (authLoading) return;

    if (isAuthenticated && authUser?.gmail_connected && state === 'initial') {
      setUserEmail(authUser.email);
      setState('success');

      // CRITICAL FIX: Call onSuccess to update wizard state and allow step advancement
      if (onSuccess) {
        onSuccess();
      }

      return;
    }
  }, [isAuthenticated, authLoading, authUser, state]);

  /**
   * Check for OAuth callback params on component mount
   */
  useEffect(() => {
    // Skip if already authenticated
    if (isAuthenticated && authUser?.gmail_connected) {
      return;
    }

    const code = searchParams.get('code');
    const stateParam = searchParams.get('state');
    const error = searchParams.get('error');

    // Handle OAuth error (user denied permission)
    if (error === 'access_denied') {
      handleError('user_denied', 'Permission denied. Please grant access to continue.');
      return;
    }

    // Handle OAuth callback with authorization code
    if (code && stateParam) {
      handleOAuthCallback(code, stateParam);
      return;
    }

    // No callback params - normal page load, fetch OAuth config
    fetchOAuthConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, isAuthenticated, authUser]);

  /**
   * Fetch OAuth configuration from backend
   */
  async function fetchOAuthConfig() {
    try {
      setState('loading');
      const response = await apiClient.gmailOAuthConfig();

      if (response.data) {
        setAuthUrl(response.data.auth_url);
        setState('initial');
      } else {
        throw new Error('Invalid OAuth config response');
      }
    } catch (error) {
      console.error('Failed to fetch OAuth config:', error);
      handleError('config_fetch_failed', 'Cannot load OAuth configuration. Please try again.');
    }
  }

  /**
   * Initiate OAuth flow by redirecting to Google
   */
  function startOAuthFlow() {
    if (!authUrl) {
      handleError('config_fetch_failed', 'OAuth configuration not loaded. Please refresh the page.');
      return;
    }

    try {
      // Backend already includes state parameter in auth_url
      // Extract state from URL and store in sessionStorage for validation on callback
      const url = new URL(authUrl);
      const stateToken = url.searchParams.get('state');

      if (!stateToken) {
        handleError('unknown', 'Invalid OAuth configuration (missing state). Please refresh the page.');
        return;
      }

      // Store state token in sessionStorage for validation on callback
      sessionStorage.setItem('oauth_state', stateToken);

      setState('loading');

      // Redirect to Google OAuth consent screen (authUrl already contains state)
      window.location.href = authUrl;
    } catch (error) {
      console.error('Failed to start OAuth flow:', error);
      handleError('unknown', 'Failed to start OAuth flow. Please try again.');
    }
  }

  /**
   * Handle OAuth callback with authorization code
   */
  async function handleOAuthCallback(code: string, stateParam: string) {
    setState('loading');

    try {
      // Validate CSRF state parameter
      const storedState = sessionStorage.getItem('oauth_state');

      if (!storedState || storedState !== stateParam) {
        handleError('invalid_state', 'Security validation failed. Please try again.');
        return;
      }

      // Exchange authorization code for JWT token
      const response = await apiClient.gmailCallback(code, stateParam);

      if (response.data && response.data.token && response.data.user) {
        const { token, user } = response.data;

        // Store JWT token in localStorage
        setToken(token);

        // Update UI with user email
        setUserEmail(user.email);

        // Clear state token from sessionStorage
        sessionStorage.removeItem('oauth_state');

        // Show success state
        setState('success');

        // Show success toast
        toast.success('Gmail account connected successfully!');

        // Call success callback if provided
        if (onSuccess) {
          onSuccess();
        }
      } else {
        throw new Error('Invalid callback response');
      }
    } catch (error) {
      console.error('OAuth callback failed:', error);
      handleError('callback_failed', 'Authentication failed. Please try again.');

      // Clear state token on error
      sessionStorage.removeItem('oauth_state');
    }
  }

  /**
   * Handle errors with appropriate messaging
   */
  function handleError(type: ErrorType, message: string) {
    setErrorType(type);
    setErrorMessage(message);
    setState('error');

    // Show error toast
    toast.error(message);

    // Call error callback if provided
    if (onError) {
      onError(message);
    }
  }

  /**
   * Retry OAuth flow after error
   */
  function retryOAuthFlow() {
    setErrorType(null);
    setErrorMessage('');
    fetchOAuthConfig();
  }

  /**
   * Render initial state: Connect Gmail button
   */
  if (state === 'initial') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-6 h-6" />
            Connect Gmail Account
          </CardTitle>
          <CardDescription>
            Authorize Mail Agent to access your Gmail account
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <AlertDescription>
              <strong>Required Permissions:</strong>
              <ul className="mt-2 ml-4 list-disc space-y-1 text-sm">
                <li>Read your emails to categorize them</li>
                <li>Send emails on your behalf (with your approval)</li>
                <li>Manage Gmail labels for organization</li>
              </ul>
            </AlertDescription>
          </Alert>

          <Button
            onClick={startOAuthFlow}
            className="w-full"
            size="lg"
          >
            <Mail className="w-4 h-4 mr-2" />
            Connect Gmail
          </Button>

          <p className="text-sm text-muted-foreground text-center">
            You&apos;ll be redirected to Google to grant permissions
          </p>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render loading state: Processing OAuth
   */
  if (state === 'loading') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="pt-6 flex flex-col items-center justify-center space-y-4 min-h-[200px]">
          <Loader2 className="w-12 h-12 animate-spin text-primary" />
          <p className="text-muted-foreground">
            {searchParams.get('code') ? 'Connecting your Gmail account...' : 'Loading...'}
          </p>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render success state: Connected
   */
  if (state === 'success') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="pt-6 flex flex-col items-center justify-center space-y-4 min-h-[200px]">
          <div className="rounded-full bg-green-500 p-3">
            <Check className="w-8 h-8 text-white" />
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-xl font-semibold">Gmail Connected!</h3>
            <p className="text-muted-foreground">
              Connected to <strong>{userEmail}</strong>
            </p>
          </div>
          <Button
            onClick={() => {
              if (onNavigate) {
                onNavigate();
              } else {
                router.push('/onboarding/telegram');
              }
            }}
            className="w-full"
            size="lg"
          >
            Continue to Telegram Setup
          </Button>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render error state: Show error message with retry
   */
  if (state === 'error') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="pt-6 space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Error:</strong> {errorMessage}
            </AlertDescription>
          </Alert>

          <div className="flex flex-col gap-2">
            <Button
              onClick={retryOAuthFlow}
              variant="outline"
              className="w-full"
            >
              Try Again
            </Button>

            {errorType === 'user_denied' && (
              <p className="text-sm text-muted-foreground text-center">
                Mail Agent requires Gmail access to function. Please grant the requested permissions.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
}
