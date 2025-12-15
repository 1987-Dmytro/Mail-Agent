import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Navbar } from '@/components/shared/Navbar';
import { MailIcon, BrainCircuitIcon, MessageSquareIcon } from 'lucide-react';

/**
 * Landing page
 * Welcome message and call-to-action
 */
export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="container flex flex-col items-center justify-center gap-8 pt-32 pb-24 md:pt-40 md:pb-32">
          <div className="flex flex-col items-center gap-4 text-center">
            <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl">
              AI-Powered Email
              <br />
              <span className="bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
                Management
              </span>
            </h1>
            <p className="max-w-[600px] text-muted-foreground md:text-xl">
              Let AI organize your inbox, categorize emails, and generate intelligent responses.
              Get notified via Telegram and approve actions with a single tap.
            </p>
          </div>

          <div className="flex flex-col gap-4 min-[400px]:flex-row mb-16 md:mb-20">
            <Button size="lg" asChild>
              <Link href="/onboarding">Get Started</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
          </div>
        </section>

        {/* Features Section */}
        <section className="container py-12 md:py-24">
          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-col items-center text-center">
                <MailIcon className="size-10 mb-2 text-primary" />
                <CardTitle>Gmail Integration</CardTitle>
                <CardDescription>
                  Seamlessly connect your Gmail account and let AI analyze your emails
                </CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <p className="text-sm text-muted-foreground">
                  OAuth 2.0 secure connection with read and send permissions
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-col items-center text-center">
                <BrainCircuitIcon className="size-10 mb-2 text-primary" />
                <CardTitle>AI Classification</CardTitle>
                <CardDescription>
                  Intelligent email sorting powered by Google Gemini
                </CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <p className="text-sm text-muted-foreground">
                  Automatic categorization and priority detection
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-col items-center text-center">
                <MessageSquareIcon className="size-10 mb-2 text-primary" />
                <CardTitle>Telegram Approval</CardTitle>
                <CardDescription>
                  Review and approve email actions via Telegram bot
                </CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <p className="text-sm text-muted-foreground">
                  Get instant notifications and respond with one tap
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-sm text-muted-foreground">
            Built with Next.js, FastAPI, and Google Gemini
          </p>
        </div>
      </footer>
    </div>
  );
}
// Final fix
