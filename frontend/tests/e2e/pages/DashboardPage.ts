import { Page, expect } from '@playwright/test';
import { mockDashboardStats } from '../fixtures/data';

/**
 * Page Object for Dashboard Page
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Represents the main dashboard with:
 * - Connection status cards (Gmail + Telegram)
 * - Email statistics (4 stat cards)
 * - Recent activity feed
 * - Auto-refresh capability
 */
export class DashboardPage {
  constructor(private page: Page) {}

  /**
   * Navigate to dashboard (requires authentication)
   * NOTE: Auth setup is done in test beforeEach, not here
   */
  async goto() {
    // Navigate to dashboard (auth already set up in test beforeEach)
    await this.page.goto('/dashboard');

    // Wait for page to load (auth check happens client-side)
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Verify connection status cards are displayed
   */
  async verifyConnectionStatusCards() {
    // Gmail connection status
    const gmailCard = this.page.getByText(/gmail/i).first();
    await expect(gmailCard).toBeVisible();

    // Telegram connection status
    const telegramCard = this.page.getByText(/telegram/i).first();
    await expect(telegramCard).toBeVisible();

    // Verify connected status indicators (use .first() to avoid strict mode)
    await expect(this.page.getByText(/connected/i).first()).toBeVisible();
  }

  /**
   * Verify email statistics are displayed
   */
  async verifyEmailStatistics() {
    // Total processed stat
    const totalProcessed = mockDashboardStats.email_stats.total_processed;
    await expect(this.page.getByText(totalProcessed.toString()).first()).toBeVisible();

    // Pending approval stat
    const pendingApproval = mockDashboardStats.email_stats.pending_approval;
    await expect(this.page.getByText(pendingApproval.toString()).first()).toBeVisible();

    // Auto sorted stat
    const autoSorted = mockDashboardStats.email_stats.auto_sorted;
    await expect(this.page.getByText(autoSorted.toString()).first()).toBeVisible();

    // Responses sent stat
    const responsesSent = mockDashboardStats.email_stats.responses_sent;
    await expect(this.page.getByText(responsesSent.toString()).first()).toBeVisible();
  }

  /**
   * Verify recent activity feed is populated
   */
  async verifyRecentActivityFeed() {
    // Check for recent activity section
    await expect(this.page.getByText(/recent activity/i).first()).toBeVisible();

    // Verify at least one activity item is displayed (email subject)
    const firstActivity = mockDashboardStats.recent_activity[0];
    if (firstActivity) {
      await expect(this.page.getByText(firstActivity.email_subject).first()).toBeVisible();
      // Verify folder name if present (type field is not displayed as text)
      if (firstActivity.folder_name) {
        await expect(this.page.getByText(firstActivity.folder_name).first()).toBeVisible();
      }
    }
  }

  /**
   * Verify time saved widget
   */
  async verifyTimeSavedWidget() {
    const todayMinutes = mockDashboardStats.time_saved.today_minutes;
    const totalMinutes = mockDashboardStats.time_saved.total_minutes;

    // Look for time saved display
    await expect(this.page.getByText(/time saved/i).first()).toBeVisible();

    // Verify time values are displayed (either today_minutes or total hours calculated from total_minutes)
    const totalHours = Math.floor(totalMinutes / 60);
    await expect(
      this.page.getByText(new RegExp(`${todayMinutes}|${totalHours}`, 'i')).first()
    ).toBeVisible();
  }

  /**
   * Wait for auto-refresh to occur (SWR polling)
   * Verifies that data is re-fetched automatically
   */
  async waitForAutoRefresh(intervalMs: number = 30000) {
    let requestCount = 0;

    // Count API requests
    await this.page.route('**/api/v1/dashboard/stats', (route) => {
      requestCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockDashboardStats,
          email_stats: {
            ...mockDashboardStats.email_stats,
            total_processed: mockDashboardStats.email_stats.total_processed + requestCount,
          },
        }),
      });
    });

    // Wait for interval + buffer
    await this.page.waitForTimeout(intervalMs + 2000);

    // Verify at least 2 requests (initial + refresh)
    expect(requestCount).toBeGreaterThanOrEqual(2);
  }

  /**
   * Verify all dashboard components are rendered
   */
  async verifyDashboardLoaded() {
    await this.verifyConnectionStatusCards();
    await this.verifyEmailStatistics();
    await this.verifyRecentActivityFeed();
    await this.verifyTimeSavedWidget();
  }

  /**
   * Navigate to folder settings from dashboard
   */
  async navigateToFolderSettings() {
    const settingsLink = this.page.getByRole('link', { name: /folder/i });
    await expect(settingsLink).toBeVisible();
    await settingsLink.click();
    await expect(this.page).toHaveURL(/\/settings\/folders/);
  }

  /**
   * Navigate to notification settings from dashboard
   */
  async navigateToNotificationSettings() {
    const settingsLink = this.page.getByRole('link', { name: /notification/i });
    await expect(settingsLink).toBeVisible();
    await settingsLink.click();
    await expect(this.page).toHaveURL(/\/settings\/notifications/);
  }
}
