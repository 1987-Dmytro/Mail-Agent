import { Page, expect } from '@playwright/test';
import { mockNotificationPreferences } from '../fixtures/data';

/**
 * Page Object for Notification Preferences Page
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Represents the notification preferences configuration page with:
 * - Batch notification toggle
 * - Batch time selection
 * - Quiet hours toggle and time range
 * - Priority immediate toggle
 * - Test notification button
 */
export class NotificationsPage {
  constructor(private page: Page) {}

  /**
   * Navigate to notification preferences page (requires authentication)
   * NOTE: Auth setup is done in test beforeEach, not here
   */
  async goto() {
    // Navigate to notifications page (auth already set up in test beforeEach)
    await this.page.goto('/settings/notifications');

    // Wait for page to load (auth check happens client-side)
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Set up mock API routes for notification preferences
   */
  private async setupNotificationAPIRoutes() {
    // GET /api/v1/notifications/preferences
    await this.page.route('**/api/v1/notifications/preferences', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockNotificationPreferences),
        });
      } else if (route.request().method() === 'PATCH') {
        // PATCH /api/v1/notifications/preferences
        const updates = route.request().postDataJSON();
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...mockNotificationPreferences, ...updates }),
        });
      }
    });

    // POST /api/v1/notifications/test
    await this.page.route('**/api/v1/notifications/test', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Test notification sent successfully' }),
      });
    });
  }

  /**
   * Toggle batch notifications
   */
  async toggleBatchNotifications(enabled: boolean) {
    const batchToggle = this.page.getByLabel(/batch notifications/i);
    await expect(batchToggle).toBeVisible();

    if (enabled) {
      await batchToggle.check();
    } else {
      await batchToggle.uncheck();
    }
  }

  /**
   * Set batch time
   */
  async setBatchTime(time: string) {
    const timeInput = this.page.locator('input[name="batch_time"]');
    await expect(timeInput).toBeVisible();
    await timeInput.fill(time);
  }

  /**
   * Toggle quiet hours
   */
  async toggleQuietHours(enabled: boolean) {
    const quietHoursToggle = this.page.getByLabel(/quiet hours/i);
    await expect(quietHoursToggle).toBeVisible();

    if (enabled) {
      await quietHoursToggle.check();
    } else {
      await quietHoursToggle.uncheck();
    }
  }

  /**
   * Set quiet hours time range
   */
  async setQuietHours(startTime: string, endTime: string) {
    const startInput = this.page.locator('input[name="quiet_hours_start"]');
    const endInput = this.page.locator('input[name="quiet_hours_end"]');

    await expect(startInput).toBeVisible();
    await expect(endInput).toBeVisible();

    await startInput.fill(startTime);
    await endInput.fill(endTime);
  }

  /**
   * Toggle priority immediate
   */
  async togglePriorityImmediate(enabled: boolean) {
    const priorityToggle = this.page.getByLabel(/priority.*immediate/i);
    await expect(priorityToggle).toBeVisible();

    if (enabled) {
      await priorityToggle.check();
    } else {
      await priorityToggle.uncheck();
    }
  }

  /**
   * Click "Test Notification" button
   */
  async sendTestNotification() {
    const testButton = this.page.getByRole('button', { name: /test notification/i });
    await expect(testButton).toBeVisible();
    await testButton.click();

    // Wait for success toast
    await expect(this.page.getByText(/test notification sent|sent successfully/i)).toBeVisible({
      timeout: 5000,
    });
  }

  /**
   * Save notification preferences
   */
  async savePreferences() {
    const saveButton = this.page.getByRole('button', { name: /save|update/i });
    await expect(saveButton).toBeVisible();
    await saveButton.click();

    // Wait for success confirmation
    await expect(this.page.getByText(/saved|updated successfully/i)).toBeVisible({
      timeout: 5000,
    });
  }

  /**
   * Update all notification preferences
   */
  async updateAllPreferences(preferences: {
    batchEnabled: boolean;
    batchTime: string;
    quietHoursEnabled: boolean;
    quietHoursStart: string;
    quietHoursEnd: string;
    priorityImmediate: boolean;
  }) {
    await this.toggleBatchNotifications(preferences.batchEnabled);

    if (preferences.batchEnabled) {
      await this.setBatchTime(preferences.batchTime);
    }

    await this.toggleQuietHours(preferences.quietHoursEnabled);

    if (preferences.quietHoursEnabled) {
      await this.setQuietHours(preferences.quietHoursStart, preferences.quietHoursEnd);
    }

    await this.togglePriorityImmediate(preferences.priorityImmediate);

    await this.savePreferences();
  }

  /**
   * Verify preferences are displayed correctly
   */
  async verifyPreferences(preferences: {
    batchEnabled: boolean;
    batchTime?: string;
    quietHoursEnabled: boolean;
    quietHoursStart?: string;
    quietHoursEnd?: string;
    priorityImmediate: boolean;
  }) {
    // Verify batch notifications
    const batchToggle = this.page.getByLabel(/batch notifications/i);
    if (preferences.batchEnabled) {
      await expect(batchToggle).toBeChecked();
    } else {
      await expect(batchToggle).not.toBeChecked();
    }

    // Verify quiet hours
    const quietHoursToggle = this.page.getByLabel(/quiet hours/i);
    if (preferences.quietHoursEnabled) {
      await expect(quietHoursToggle).toBeChecked();
    } else {
      await expect(quietHoursToggle).not.toBeChecked();
    }

    // Verify priority immediate
    const priorityToggle = this.page.getByLabel(/priority.*immediate/i);
    if (preferences.priorityImmediate) {
      await expect(priorityToggle).toBeChecked();
    } else {
      await expect(priorityToggle).not.toBeChecked();
    }
  }
}
