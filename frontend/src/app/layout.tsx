import type { Metadata } from "next";
import "./globals.css";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { OnboardingRedirect } from "@/components/shared/OnboardingRedirect";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "Mail Agent - AI Email Management",
  description: "Intelligent email organization and response generation powered by AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {/* Skip to main content link for keyboard accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
        >
          Skip to main content
        </a>
        <ErrorBoundary>
          <OnboardingRedirect>
            <main id="main-content">
              {children}
            </main>
          </OnboardingRedirect>
          <Toaster />
        </ErrorBoundary>
      </body>
    </html>
  );
}
// Trigger workflow
