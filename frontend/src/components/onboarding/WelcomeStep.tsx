import { Mail, Bot, FolderKanban, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { StepProps } from './OnboardingWizard';

/**
 * WelcomeStep - Step 1 of onboarding wizard
 *
 * Displays:
 * - Mail Agent logo and tagline
 * - Core benefits (AI sorting, Telegram approval, multilingual responses)
 * - What user will configure (Gmail, Telegram, Folders)
 * - Estimated time to complete (5-10 minutes)
 * - "Get Started" button to proceed to Step 2
 * - Skip onboarding link for advanced users
 *
 * AC2: Step 1 (Welcome) - Welcome screen explaining Mail Agent benefits and what to expect
 */
export default function WelcomeStep({ onNext }: StepProps) {
  /**
   * Handle Get Started button click
   * Proceeds to Step 2 (Gmail Connection)
   */
  const handleGetStarted = () => {
    onNext();
  };

  /**
   * Handle skip onboarding click
   * Advanced users can skip setup and go directly to dashboard
   */
  const handleSkip = () => {
    // TODO: Navigate to dashboard (implement in Subtask 2.6)
    console.log('Skip onboarding clicked - redirect to /dashboard');
  };

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="text-center">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-primary/10 p-4">
            <Mail className="h-12 w-12 text-primary" />
          </div>
        </div>
        <h1 className="mb-2 text-3xl font-bold leading-tight">Welcome to Mail Agent</h1>
        <p className="text-lg text-muted-foreground">
          Never miss an important email again
        </p>
      </div>

      {/* Core benefits */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Here&apos;s how it works
          </CardTitle>
          <CardDescription>
            Intelligent email management with AI and Telegram
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold leading-tight">AI Email Sorting</h3>
              <p className="text-sm text-muted-foreground leading-normal">
                AI reads every email and suggests the right folder—so you don&apos;t have to
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <svg
                className="h-6 w-6 text-primary"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold leading-tight">One-Tap Telegram Approval</h3>
              <p className="text-sm text-muted-foreground leading-normal">
                Approve with one tap on Telegram—no need to open your inbox
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <FolderKanban className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold leading-tight">Smart Folder Management</h3>
              <p className="text-sm text-muted-foreground leading-normal">
                Set up folders that match how you work—perfect for freelancers and busy professionals
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Setup steps preview */}
      <Card>
        <CardHeader>
          <CardTitle>5-Minute Setup</CardTitle>
          <CardDescription>We&apos;ll walk you through everything—it&apos;s easier than you think</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3 text-sm">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              1
            </div>
            <span>Connect Gmail <span className="text-muted-foreground">(30 seconds)</span></span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              2
            </div>
            <span>Link Telegram <span className="text-muted-foreground">(1 minute)</span></span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              3
            </div>
            <span>Create your folders <span className="text-muted-foreground">(2 minutes)</span></span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              4
            </div>
            <span>You&apos;re ready to go!</span>
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex flex-col gap-3">
        <Button
          onClick={handleGetStarted}
          size="lg"
          className="w-full"
        >
          Get Started
        </Button>

        <Button
          onClick={handleSkip}
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
        >
          Skip setup—I&apos;ll configure this later
        </Button>
      </div>
    </div>
  );
}
