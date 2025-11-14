import { Metadata } from 'next';
import NotificationSettings from '@/components/settings/NotificationSettings';

/**
 * Metadata for notification settings page
 */
export const metadata: Metadata = {
  title: 'Notification Preferences | Mail Agent',
  description: 'Configure when and how you receive Telegram notifications',
};

/**
 * Notification Preferences Settings Page
 * Server Component that wraps the client-side NotificationSettings component
 */
export default function NotificationSettingsPage() {
  return (
    <div className="container mx-auto max-w-4xl py-8 px-4">
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notification Preferences</h1>
          <p className="text-muted-foreground mt-2">
            Configure when and how you receive Telegram notifications
          </p>
        </div>

        {/* Notification Settings Component */}
        <NotificationSettings />
      </div>
    </div>
  );
}
