import { TelegramLink } from './TelegramLink';
import type { StepProps } from './OnboardingWizard';

/**
 * TelegramStep - Step 3 of onboarding wizard
 *
 * Wraps the existing TelegramLink component from Story 4.3
 * Handles Telegram bot linking and notifies wizard when connection is successful
 *
 * AC4: Step 3 (Telegram) - Telegram linking page (reuses existing Telegram component from Story 4.3)
 * AC8: Steps cannot proceed until required actions completed (Telegram linked before Step 4)
 */
export default function TelegramStep({ onStepComplete, onNext }: StepProps) {
  /**
   * Handle successful Telegram linking
   * Updates wizard state to enable Next button
   */
  const handleSuccess = () => {
    // Update wizard state: Telegram connected
    onStepComplete({
      telegramConnected: true,
      telegramUsername: undefined, // TelegramLink doesn't expose username in callback, but it's stored in hook state
      gmailConnected: true, // Preserve from previous step
      folders: [],
      currentStep: 3,
      lastUpdated: new Date().toISOString(),
    });
  };

  /**
   * Handle Telegram linking error
   * Shows error message but keeps user on same step
   */
  const handleError = (error: string) => {
    console.error('Telegram linking error:', error);
    // Error is already displayed by TelegramLink component via toast
    // No need to update wizard state - user can retry
  };

  return (
    <div className="flex flex-col items-center text-center space-y-6">
      {/* Reuse existing TelegramLink component from Story 4.3 */}
      {/* Pass onNext as onNavigate to integrate with wizard navigation */}
      <TelegramLink onSuccess={handleSuccess} onError={handleError} onNavigate={onNext} />
    </div>
  );
}
