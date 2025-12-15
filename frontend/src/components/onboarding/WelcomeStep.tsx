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
    <div className="flex flex-col items-center text-center space-y-8 max-w-2xl mx-auto">
      {/* Welcome header */}
      <div className="w-full space-y-4">
        <div className="mb-6 flex justify-center">
          <div className="rounded-full bg-gradient-to-br from-primary/20 to-primary/10 p-5 shadow-lg shadow-primary/10">
            <Mail className="h-14 w-14 text-primary" />
          </div>
        </div>
        <h1 className="text-4xl font-bold leading-tight tracking-tight">Welcome to Mail Agent</h1>
        <p className="text-xl text-muted-foreground max-w-md mx-auto">
          Never miss an important email again
        </p>
      </div>

      {/* How it works explanation */}
      <Card className="w-full shadow-md border-primary/30 bg-primary/5">
        <CardContent className="py-5">
          <div className="space-y-3 text-left">
            <h3 className="font-semibold text-base flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              First-Time Setup
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              This is a one-time setup process. You'll connect your services, create a password,
              and then use the login page for all future visits. Let's get started!
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Core benefits */}
      <Card className="w-full shadow-md border-border/50">
        <CardHeader className="space-y-3 pb-6">
          <CardTitle className="flex items-center justify-center gap-2 text-2xl">
            <Sparkles className="h-6 w-6 text-primary" />
            Here&apos;s how it works
          </CardTitle>
          <CardDescription className="text-base">
            Intelligent email management with AI and Telegram
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 p-3">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div className="max-w-sm mx-auto">
              <h3 className="font-semibold text-base mb-1.5">AI Email Sorting</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                AI reads every email and suggests the right folder—so you don&apos;t have to
              </p>
            </div>
          </div>

          <div className="flex flex-col items-center text-center space-y-3">
            <div className="rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 p-3">
              <svg
                className="h-6 w-6 text-primary"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
            </div>
            <div className="max-w-sm mx-auto">
              <h3 className="font-semibold text-base mb-1.5">One-Tap Telegram Approval</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Approve with one tap on Telegram—no need to open your inbox
              </p>
            </div>
          </div>

          <div className="flex flex-col items-center text-center space-y-3">
            <div className="rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 p-3">
              <FolderKanban className="h-6 w-6 text-primary" />
            </div>
            <div className="max-w-sm mx-auto">
              <h3 className="font-semibold text-base mb-1.5">Smart Folder Management</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Set up folders that match how you work—perfect for freelancers and busy professionals
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Setup steps preview */}
      <Card className="w-full shadow-md border-border/50">
        <CardHeader className="space-y-3 pb-6">
          <CardTitle className="text-2xl">5-Minute Setup</CardTitle>
          <CardDescription className="text-base">We&apos;ll walk you through everything—it&apos;s easier than you think</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/80 text-sm font-bold text-primary-foreground shadow-sm">
              1
            </div>
            <span className="text-base">Connect Gmail <span className="text-muted-foreground text-sm">(30 seconds)</span></span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/80 text-sm font-bold text-primary-foreground shadow-sm">
              2
            </div>
            <span className="text-base">Link Telegram <span className="text-muted-foreground text-sm">(1 minute)</span></span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/80 text-sm font-bold text-primary-foreground shadow-sm">
              3
            </div>
            <span className="text-base">Create your folders <span className="text-muted-foreground text-sm">(2 minutes)</span></span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/80 text-sm font-bold text-primary-foreground shadow-sm">
              4
            </div>
            <span className="text-base">Set your password <span className="text-muted-foreground text-sm">(30 seconds)</span></span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-green-500 to-green-600 text-sm font-bold text-white shadow-sm">
              ✓
            </div>
            <span className="text-base font-medium">You&apos;re ready to go!</span>
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex flex-col gap-4 w-full pt-2">
        <Button
          onClick={handleGetStarted}
          size="lg"
          className="w-full h-12 text-base font-semibold shadow-md hover:shadow-lg transition-all"
        >
          Get Started
        </Button>

        <Button
          onClick={handleSkip}
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground"
        >
          Skip setup—I&apos;ll configure this later
        </Button>
      </div>
    </div>
  );
}
