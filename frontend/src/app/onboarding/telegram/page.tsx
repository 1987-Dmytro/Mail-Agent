import { TelegramLink } from '@/components/onboarding/TelegramLink';

/**
 * Telegram Onboarding Page
 *
 * Step 2 of the onboarding wizard
 * Allows users to link their Telegram account to receive email notifications
 *
 * Page route: /onboarding/telegram
 * Previous: /onboarding/gmail (Gmail OAuth)
 * Next: /dashboard (after successful linking)
 */
export default function TelegramOnboardingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <TelegramLink />
    </div>
  );
}
