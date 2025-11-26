'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';

/**
 * Authentication status response
 */
interface AuthStatus {
  authenticated: boolean;
  user?: {
    id: number;
    email: string;
    gmail_connected: boolean;
    telegram_connected: boolean;
    onboarding_completed?: boolean;
  };
}

/**
 * Hook return value
 */
interface UseAuthStatusReturn {
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** Whether auth status is loading */
  isLoading: boolean;
  /** Error message if auth check failed */
  error: string | null;
  /** User object if authenticated */
  user: AuthStatus['user'] | null;
  /** Refresh authentication status */
  refresh: () => Promise<void>;
}

/**
 * Custom hook to check authentication status
 *
 * Checks if user is already authenticated on page load.
 * Used for connection persistence across page refreshes (AC: 6).
 *
 * @returns Authentication status, loading state, and refresh function
 *
 * @example
 * ```tsx
 * const { isAuthenticated, isLoading, user, refresh } = useAuthStatus();
 *
 * if (isLoading) return <Spinner />;
 * if (isAuthenticated) return <Dashboard user={user} />;
 * return <LoginPage />;
 * ```
 */
export function useAuthStatus(): UseAuthStatusReturn {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<AuthStatus['user'] | null>(null);

  /**
   * Check authentication status via API
   */
  async function checkAuthStatus() {
    try {
      setIsLoading(true);
      setError(null);

      const response = await apiClient.authStatus();

      // Handle both wrapped { data: {...} } and unwrapped { authenticated: ... } responses
      // Backend returns unwrapped format: { authenticated: boolean, user?: {...} }
      const authData = 'data' in response && response.data ? response.data : response;

      if (authData && 'authenticated' in authData) {
        setIsAuthenticated(authData.authenticated);
        setUser(authData.user || null);
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (err) {
      console.error('Failed to check auth status:', err);
      setError('Failed to check authentication status');
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }

  /**
   * Check auth status on mount
   */
  useEffect(() => {
    checkAuthStatus();
  }, []);

  return {
    isAuthenticated,
    isLoading,
    error,
    user,
    refresh: checkAuthStatus,
  };
}
