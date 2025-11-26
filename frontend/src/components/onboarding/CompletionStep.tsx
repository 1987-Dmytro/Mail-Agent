import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Check, Mail, MessageCircle, FolderKanban, Loader2, PartyPopper } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import type { StepProps } from './OnboardingWizard';

/**
 * CompletionStep - Step 5 of onboarding wizard
 *
 * Displays:
 * - Success animation or celebration graphic
 * - Summary of configured items (Gmail, Telegram, folders)
 * - "Go to Dashboard" button (primary action)
 *
 * On button click:
 * - Call apiClient.updateUser({ onboarding_completed: true })
 * - Clear localStorage onboarding progress
 * - Navigate to /dashboard using Next.js router
 * - Show error message if backend update fails
 *
 * AC6: Step 5 (Complete) - Completion celebration screen with "Go to Dashboard" button
 * AC10: Completion updates user.onboarding_completed = true in backend
 */
export default function CompletionStep({ currentState }: StepProps) {
  const router = useRouter();
  const [isCompleting, setIsCompleting] = useState<boolean>(false);

  /**
   * Handle "Go to Dashboard" button click
   * Completes onboarding by updating backend and clearing localStorage
   */
  const handleGoToDashboard = async () => {
    setIsCompleting(true);

    try {
      // Update backend: mark onboarding as completed (AC10)
      await apiClient.completeOnboarding();

      // Clear localStorage onboarding progress
      localStorage.removeItem('onboarding_progress');

      // Show success toast
      toast.success('Setup complete! Your first email is probably already sorted 🎉');

      // Navigate to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
      toast.error('Oops! Something went wrong. Let\'s try that again.');

      // Even if API fails, still redirect (user mostly done with onboarding)
      // The OnboardingRedirect component will handle any incomplete state
      router.push('/dashboard');
    } finally {
      setIsCompleting(false);
    }
  };

  return (
    <div className="flex flex-col items-center text-center space-y-6">
      {/* Celebration header */}
      <div className="w-full space-y-3">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-green-100 p-6 dark:bg-green-900/20">
            <PartyPopper className="h-16 w-16 text-green-600 dark:text-green-400" />
          </div>
        </div>
        <h1 className="mb-2 text-3xl font-bold leading-tight">You&apos;re All Set! 🎉</h1>
        <p className="text-lg text-muted-foreground">
          Your inbox is now on autopilot. Here&apos;s what we set up:
        </p>
      </div>

      {/* Summary card */}
      <Card className="border-green-500/50 bg-green-50/50 dark:bg-green-900/10">
        <CardContent className="space-y-4 py-6">

          {/* Gmail connected */}
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span className="font-semibold">Gmail connected</span>
              </div>
              {currentState.gmailEmail && (
                <p className="text-sm text-muted-foreground">{currentState.gmailEmail}</p>
              )}
            </div>
          </div>

          {/* Telegram linked */}
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-muted-foreground" />
                <span className="font-semibold">Telegram linked</span>
              </div>
              {currentState.telegramUsername && (
                <p className="text-sm text-muted-foreground">@{currentState.telegramUsername}</p>
              )}
            </div>
          </div>

          {/* Folders configured */}
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <FolderKanban className="h-4 w-4 text-muted-foreground" />
                <span className="font-semibold">
                  {currentState.folders.length} folder{currentState.folders.length !== 1 ? 's' : ''}{' '}
                  configured
                </span>
              </div>
              {currentState.folders.length > 0 && (
                <p className="text-sm text-muted-foreground">
                  {currentState.folders.map((f) => f.name).join(', ')}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* What happens next */}
      <Card>
        <CardContent className="space-y-3 py-6">
          <h3 className="font-semibold leading-tight">What happens next?</h3>
          <ul className="space-y-3 text-sm text-muted-foreground leading-normal">
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>We&apos;ll watch your inbox for new emails</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>AI suggests the best folder for each email</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Get instant approval requests on Telegram</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Tap once to approve, and we&apos;ll file it away</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Go to Dashboard button */}
      <Button
        onClick={handleGoToDashboard}
        disabled={isCompleting}
        size="lg"
        className="w-full"
      >
        {isCompleting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Almost there...
          </>
        ) : (
          'Take Me to My Dashboard'
        )}
      </Button>
    </div>
  );
}
