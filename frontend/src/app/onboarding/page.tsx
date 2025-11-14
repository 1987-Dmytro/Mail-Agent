import { Metadata } from 'next';
import OnboardingWizard from '@/components/onboarding/OnboardingWizard';

/**
 * Metadata for onboarding page
 * Provides SEO-friendly page information
 */
export const metadata: Metadata = {
  title: 'Get Started | Mail Agent',
  description: 'Complete your Mail Agent setup in just a few steps',
};

/**
 * Onboarding page route
 * Wraps OnboardingWizard component for multi-step setup flow
 *
 * Route: /onboarding
 * Accessible by: First-time users (user.onboarding_completed = false)
 * Redirect logic: Implemented in layout.tsx or middleware (Subtask 2.6)
 */
export default function OnboardingPage() {
  return <OnboardingWizard />;
}
