import { GmailConnect } from './GmailConnect';
import type { StepProps } from './OnboardingWizard';

/**
 * GmailStep - Step 2 of onboarding wizard
 *
 * Wraps the existing GmailConnect component from Story 4.2
 * Handles Gmail OAuth flow and notifies wizard when connection is successful
 *
 * AC3: Step 2 (Gmail) - Gmail connection page (reuses existing Gmail OAuth component from Story 4.2)
 * AC8: Steps cannot proceed until required actions completed (Gmail connected before Step 3)
 */
export default function GmailStep({ onStepComplete, onNext }: StepProps) {
  /**
   * Handle successful Gmail connection
   * Updates wizard state to enable Next button
   */
  const handleSuccess = () => {
    // Update wizard state: Gmail connected
    onStepComplete({
      gmailConnected: true,
      telegramConnected: false,
      folders: [],
      gmailEmail: undefined, // GmailConnect doesn't expose email in callback, but it's stored in auth state
      currentStep: 2,
      lastUpdated: new Date().toISOString(),
    });
  };

  /**
   * Handle Gmail connection error
   * Shows error message but keeps user on same step
   */
  const handleError = (error: string) => {
    console.error('Gmail connection error:', error);
    // Error is already displayed by GmailConnect component via toast
    // No need to update wizard state - user can retry
  };

  return (
    <div>
      {/* Reuse existing GmailConnect component from Story 4.2 */}
      <GmailConnect onSuccess={handleSuccess} onError={handleError} onNavigate={onNext} />
    </div>
  );
}
