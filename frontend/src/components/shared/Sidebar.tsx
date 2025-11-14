'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { HomeIcon, SettingsIcon, MailIcon } from 'lucide-react';

/**
 * Sidebar navigation component
 * Vertical navigation menu for desktop
 */
export function Sidebar() {
  const pathname = usePathname();

  const links = [
    {
      href: '/dashboard',
      label: 'Dashboard',
      icon: HomeIcon,
    },
    {
      href: '/onboarding',
      label: 'Onboarding',
      icon: MailIcon,
    },
    {
      href: '/settings',
      label: 'Settings',
      icon: SettingsIcon,
    },
  ];

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-border bg-muted/40">
      <div className="flex-1 overflow-auto py-6">
        <nav className="grid gap-1 px-4">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href || pathname?.startsWith(`${link.href}/`);

            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <Icon className="size-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
