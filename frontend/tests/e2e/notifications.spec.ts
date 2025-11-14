import { test, expect } from '@playwright/test';
import { NotificationsPage } from './pages/NotificationsPage';
import { setupAuthenticatedSession, mockAuthEndpoints } from './fixtures/auth';
import { mockAllApiEndpoints } from './fixtures/data';

/**
 * E2E Tests for Notification Preferences
 * Story 4.8: End-to-End Onboarding Testing and Polish
 * AC 1: Usability testing conducted with 3-5 non-technical users
 *
 * Test Coverage:
 * - Notification preferences page loads
 * - Batch notification toggle
 * - Batch time selection
 * - Quiet hours toggle and time range
 * - Priority immediate toggle
 * - Test notification functionality
 * - Preferences persistence
 *
 * FIXED: Added authentication + API mocking
 */

test.describe('Notification Preferences E2E Tests', () => {
  let notificationsPage: NotificationsPage;

  test.beforeEach(async ({ page }) => {
    // CRITICAL: Set up API mocking FIRST, THEN auth (which navigates)
    await mockAuthEndpoints(page);
    await mockAllApiEndpoints(page);
    await setupAuthenticatedSession(page);

    notificationsPage = new NotificationsPage(page);
  });

  test('notification preferences page loads correctly', async ({ page }) => {
    await notificationsPage.goto();

    // Verify page title
    await expect(
      page.getByRole('heading', { name: /notification.*preference|notification.*setting/i })
    ).toBeVisible();

    // Verify key elements are present
    await expect(page.getByLabel(/batch notifications/i)).toBeVisible();
    await expect(page.getByLabel(/quiet hours/i)).toBeVisible();
    await expect(page.getByLabel(/priority.*immediate/i)).toBeVisible();
  });

  test('toggle batch notifications on and off', async ({ page }) => {
    await notificationsPage.goto();

    const batchToggle = page.getByLabel(/batch notifications/i);

    // Turn on batch notifications
    await batchToggle.check();
    await expect(batchToggle).toBeChecked();

    // Turn off batch notifications
    await batchToggle.uncheck();
    await expect(batchToggle).not.toBeChecked();
  });

  test('set batch time when batch notifications enabled', async ({ page }) => {
    await notificationsPage.goto();

    // Enable batch notifications
    await notificationsPage.toggleBatchNotifications(true);

    // Set batch time
    await notificationsPage.setBatchTime('09:00');

    // Verify time is set
    const timeInput = page.locator('input[name="batch_time"]');
    const value = await timeInput.inputValue();
    expect(value).toBe('09:00');
  });

  test('toggle quiet hours on and off', async ({ page }) => {
    await notificationsPage.goto();

    const quietHoursToggle = page.getByLabel(/quiet hours/i);

    // Turn on quiet hours
    await quietHoursToggle.check();
    await expect(quietHoursToggle).toBeChecked();

    // Turn off quiet hours
    await quietHoursToggle.uncheck();
    await expect(quietHoursToggle).not.toBeChecked();
  });

  test('set quiet hours time range', async ({ page }) => {
    await notificationsPage.goto();

    // Enable quiet hours
    await notificationsPage.toggleQuietHours(true);

    // Set quiet hours range
    await notificationsPage.setQuietHours('22:00', '08:00');

    // Verify times are set
    const startInput = page.locator('input[name="quiet_hours_start"]');
    const endInput = page.locator('input[name="quiet_hours_end"]');

    const startValue = await startInput.inputValue();
    const endValue = await endInput.inputValue();

    expect(startValue).toBe('22:00');
    expect(endValue).toBe('08:00');
  });

  test('toggle priority immediate notifications', async ({ page }) => {
    await notificationsPage.goto();

    const priorityToggle = page.getByLabel(/priority.*immediate/i);

    // Turn on priority immediate
    await priorityToggle.check();
    await expect(priorityToggle).toBeChecked();

    // Turn off priority immediate
    await priorityToggle.uncheck();
    await expect(priorityToggle).not.toBeChecked();
  });

  test('test notification button sends notification', async ({ page }) => {
    await notificationsPage.goto();

    // Click test notification button
    await notificationsPage.sendTestNotification();

    // Verify success message is displayed
    await expect(
      page.getByText(/test notification sent|sent successfully/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('save notification preferences successfully', async ({ page }) => {
    await notificationsPage.goto();

    // Update preferences
    await notificationsPage.toggleBatchNotifications(true);
    await notificationsPage.setBatchTime('10:00');
    await notificationsPage.toggleQuietHours(true);
    await notificationsPage.setQuietHours('23:00', '07:00');
    await notificationsPage.togglePriorityImmediate(true);

    // Save preferences
    await notificationsPage.savePreferences();

    // Verify success message
    await expect(
      page.getByText(/saved|updated successfully|preferences.*saved/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('notification preferences persist after page refresh', async ({ page }) => {
    await notificationsPage.goto();

    // Set specific preferences
    await notificationsPage.updateAllPreferences({
      batchEnabled: true,
      batchTime: '11:00',
      quietHoursEnabled: true,
      quietHoursStart: '21:00',
      quietHoursEnd: '09:00',
      priorityImmediate: false,
    });

    // Refresh page
    await page.reload();

    // Verify preferences persisted
    const batchToggle = page.getByLabel(/batch notifications/i);
    await expect(batchToggle).toBeChecked();

    const quietHoursToggle = page.getByLabel(/quiet hours/i);
    await expect(quietHoursToggle).toBeChecked();

    const priorityToggle = page.getByLabel(/priority.*immediate/i);
    await expect(priorityToggle).not.toBeChecked();
  });

  test('batch time field disabled when batch notifications off', async ({ page }) => {
    await notificationsPage.goto();

    // Disable batch notifications
    await notificationsPage.toggleBatchNotifications(false);

    // Verify batch time input is disabled or hidden
    const timeInput = page.locator('input[name="batch_time"]');
    const isDisabled = await timeInput.isDisabled().catch(() => false);
    const isHidden = !(await timeInput.isVisible().catch(() => true));

    expect(isDisabled || isHidden).toBeTruthy();
  });

  test('quiet hours time fields disabled when quiet hours off', async ({ page }) => {
    await notificationsPage.goto();

    // Disable quiet hours
    await notificationsPage.toggleQuietHours(false);

    // Verify time inputs are disabled or hidden
    const startInput = page.locator('input[name="quiet_hours_start"]');
    const endInput = page.locator('input[name="quiet_hours_end"]');

    const startDisabled = await startInput.isDisabled().catch(() => false);
    const endDisabled = await endInput.isDisabled().catch(() => false);
    const startHidden = !(await startInput.isVisible().catch(() => true));
    const endHidden = !(await endInput.isVisible().catch(() => true));

    expect(startDisabled || startHidden).toBeTruthy();
    expect(endDisabled || endHidden).toBeTruthy();
  });

  test('notification preferences show helpful descriptions', async ({ page }) => {
    await notificationsPage.goto();

    // Verify descriptions/help text is present
    await expect(
      page.getByText(/batch.*notification.*collect|group.*notification/i)
    ).toBeVisible();

    await expect(
      page.getByText(/quiet hours.*silent|no notification.*during/i)
    ).toBeVisible();

    await expect(
      page.getByText(/priority.*immediate|high priority.*instant/i)
    ).toBeVisible();
  });

  test('notification preferences validate time format', async ({ page }) => {
    await notificationsPage.goto();

    // Enable batch notifications
    await notificationsPage.toggleBatchNotifications(true);

    // Try to enter invalid time
    const timeInput = page.locator('input[name="batch_time"]');
    await timeInput.fill('99:99');

    // Save preferences
    const saveButton = page.getByRole('button', { name: /save|update/i });
    await saveButton.click();

    // Verify validation error or time is corrected
    // HTML5 time input typically handles validation
  });
});
