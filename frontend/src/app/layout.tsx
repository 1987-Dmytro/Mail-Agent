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
        <ErrorBoundary>
          <OnboardingRedirect>
            {children}
          </OnboardingRedirect>
          <Toaster />
        </ErrorBoundary>
      </body>
    </html>
  );
}
