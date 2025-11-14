'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { MenuIcon } from 'lucide-react';

interface NavbarProps {
  onMenuClick?: () => void;
}

/**
 * Navigation bar component
 * Displays logo, navigation links, and user menu
 */
export function Navbar({ onMenuClick }: NavbarProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className="mr-2 md:hidden"
          onClick={onMenuClick}
          aria-label="Toggle menu"
        >
          <MenuIcon className="size-5" />
        </Button>

        {/* Logo */}
        <Link href="/" className="mr-6 flex items-center space-x-2">
          <span className="text-xl font-bold bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
            Mail Agent
          </span>
        </Link>

        {/* Navigation links */}
        <nav className="hidden md:flex flex-1 items-center space-x-6 text-sm font-medium">
          <Link
            href="/dashboard"
            className="transition-colors hover:text-foreground/80 text-foreground/60"
          >
            Dashboard
          </Link>
          <Link
            href="/settings"
            className="transition-colors hover:text-foreground/80 text-foreground/60"
          >
            Settings
          </Link>
        </nav>

        {/* User actions */}
        <div className="flex flex-1 items-center justify-end space-x-2">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/onboarding">Get Started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
