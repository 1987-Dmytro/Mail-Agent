'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStatus } from '@/hooks/useAuthStatus';

/**
 * OnboardingRedirect - First-time user redirect handler
 *
 * Responsibilities:
 * - Check user.onboarding_completed status on authenticated routes
 * - If false AND not already on /onboarding → Redirect to /onboarding
 * - Allow access to /onboarding even if completed (support re-running setup)
 *
 * AC11: First-time users automatically redirected to /onboarding on login
 *
 * Placement: Wraps app content in layout.tsx
 */
export function OnboardingRedirect({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, user } = useAuthStatus();

  useEffect(() => {
    // Wait for auth status to load
    if (isLoading) return;

    // Only redirect authenticated users
    if (!isAuthenticated) return;

    // Skip redirect if already on onboarding page
    if (pathname === '/onboarding') return;

    // Skip redirect if user has completed onboarding
    if (user?.onboarding_completed) return;

    // Redirect to onboarding if not completed
    if (user && !user.onboarding_completed) {
      console.log('[OnboardingRedirect] First-time user detected, redirecting to /onboarding');
      router.push('/onboarding');
    }
  }, [isAuthenticated, isLoading, user, pathname, router]);

  return <>{children}</>;
}
