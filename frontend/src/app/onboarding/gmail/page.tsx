import { Suspense } from 'react';
import { GmailConnect } from '@/components/onboarding/GmailConnect';
import { Loader2 } from 'lucide-react';

/**
 * Gmail OAuth Connection Page
 *
 * Onboarding wizard step 1: Connect Gmail account
 *
 * This is a server component by default (Next.js 16).
 * The GmailConnect component is a client component that handles OAuth.
 */
export default function GmailOnboardingPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-2xl space-y-6">
        {/* Onboarding Progress */}
        <div className="text-center space-y-2">
          <p className="text-sm text-muted-foreground">Step 1 of 3</p>
          <h1 className="text-3xl font-bold tracking-tight">Connect Your Gmail</h1>
          <p className="text-muted-foreground">
            Let&apos;s start by connecting your Gmail account
          </p>
        </div>

        {/* Progress Bar */}
        <div className="flex gap-2">
          <div className="flex-1 h-2 rounded-full bg-primary" />
          <div className="flex-1 h-2 rounded-full bg-muted" />
          <div className="flex-1 h-2 rounded-full bg-muted" />
        </div>

        {/* Gmail Connection Component */}
        <Suspense
          fallback={
            <div className="flex justify-center items-center min-h-[300px]">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          }
        >
          <GmailConnect />
        </Suspense>
      </div>
    </main>
  );
}

/**
 * Page metadata
 */
export const metadata = {
  title: 'Connect Gmail - Mail Agent',
  description: 'Connect your Gmail account to get started with Mail Agent',
};
