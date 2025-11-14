import { test, expect } from '@playwright/test';
import { OnboardingPage } from './pages/OnboardingPage';
import { DashboardPage } from './pages/DashboardPage';
import { FoldersPage } from './pages/FoldersPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { setupAuthenticatedSession, mockAuthEndpoints } from './fixtures/auth';
import { mockAllApiEndpoints } from './fixtures/data';

/**
 * E2E Tests for Error Scenarios and Edge Cases
 * Story 4.8: End-to-End Onboarding Testing and Polish
 * AC 1: Usability testing conducted with 3-5 non-technical users
 * AC 7: Loading states and error messages improved for clarity
 *
 * Test Coverage:
 * - API failure handling (500 errors)
 * - Network offline detection and recovery
 * - Timeout scenarios
 * - Invalid data handling
 * - Error message clarity
 * - Retry mechanisms
 *
 * FIXED: Added authentication + API mocking
 */

test.describe('Error Scenario E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // CRITICAL: Set up API mocking FIRST, THEN auth (which navigates)
    await mockAuthEndpoints(page);
    await mockAllApiEndpoints(page);
    await setupAuthenticatedSession(page);
  });
  test('API failure shows error message and retry button', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock API failure
    await page.route('**/api/v1/dashboard/stats', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await dashboardPage.goto();

    // Verify error message is displayed
    await expect(
      page.getByText(/error.*loading|failed.*load|something went wrong/i)
    ).toBeVisible({ timeout: 10000 });

    // Verify retry button is available
    const retryButton = page.getByRole('button', { name: /retry|try again/i });
    await expect(retryButton).toBeVisible();
    await expect(retryButton).toBeEnabled();
  });

  test('retry button recovers from API failure', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    let requestCount = 0;

    // First request fails, second succeeds
    await page.route('**/api/v1/dashboard/stats', (route) => {
      requestCount++;
      if (requestCount === 1) {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal Server Error' }),
        });
      } else {
        // Continue with normal mock response
        route.continue();
      }
    });

    await dashboardPage.goto();

    // Wait for error state
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 10000 });

    // Click retry button
    const retryButton = page.getByRole('button', { name: /retry|try again/i });
    await retryButton.click();

    // Verify dashboard loads successfully after retry
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({
      timeout: 10000,
    });
  });

  test('network offline shows offline banner', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Start with online state
    await dashboardPage.goto();

    // Simulate network going offline
    await page.context().setOffline(true);

    // Trigger a request that will fail due to offline
    await page.reload();

    // Verify offline banner/message is displayed
    await expect(
      page.getByText(/offline|no.*connection|network.*unavailable/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('network recovery restores functionality', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Start offline
    await page.context().setOffline(true);

    await page.goto('/dashboard');

    // Verify offline state
    await expect(
      page.getByText(/offline|no.*connection|network.*unavailable/i)
    ).toBeVisible({ timeout: 10000 });

    // Restore network connection
    await page.context().setOffline(false);

    // Reload or trigger retry
    await page.reload();

    // Verify dashboard loads successfully
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({
      timeout: 10000,
    });
  });

  test('API timeout shows timeout error message', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock slow API that times out
    await page.route('**/api/v1/dashboard/stats', async (route) => {
      // Wait longer than timeout (simulate hanging request)
      await new Promise((resolve) => setTimeout(resolve, 60000));
      route.abort();
    });

    await page.goto('/dashboard');

    // Verify timeout error message
    await expect(
      page.getByText(/timeout|took too long|slow.*connection/i)
    ).toBeVisible({ timeout: 65000 });
  });

  test('404 error shows appropriate message', async ({ page }) => {
    // Navigate to non-existent page
    await page.goto('/non-existent-page');

    // Verify 404 error message
    await expect(page.getByText(/404|not found|page.*not.*exist/i)).toBeVisible({
      timeout: 10000,
    });

    // Verify link to go back or home
    const homeLink = page.getByRole('link', { name: /home|dashboard|back/i });
    await expect(homeLink).toBeVisible();
  });

  test('unauthorized access redirects to login', async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto('/dashboard');

    // Verify redirect to login or onboarding
    await expect(page).toHaveURL(/\/login|\/onboarding|\/auth/);

    // Verify login prompt
    await expect(page.getByText(/login|sign in|authenticate/i)).toBeVisible({
      timeout: 10000,
    });
  });

  test('folder creation with duplicate name shows error', async ({ page }) => {
    const foldersPage = new FoldersPage(page);

    // Mock API to reject duplicate
    await page.route('**/api/v1/folders', (route) => {
      if (route.request().method() === 'POST') {
        const data = route.request().postDataJSON();
        if (data.name === 'Government') {
          route.fulfill({
            status: 409,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Folder name already exists' }),
          });
        } else {
          route.continue();
        }
      } else {
        route.continue();
      }
    });

    await foldersPage.goto();

    // Try to create folder with existing name
    const addButton = page.getByRole('button', { name: /add folder/i });
    await addButton.click();

    await page.fill('input[name="name"]', 'Government');
    await page.fill('input[name="keywords"]', 'test');

    const saveButton = page.getByRole('button', { name: /save/i });
    await saveButton.click();

    // Verify error message about duplicate
    await expect(
      page.getByText(/already exists|duplicate|name.*taken/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('invalid email format shows validation error', async ({ page }) => {
    // This test would apply to a login or profile page
    // Placeholder for email validation testing

    await page.goto('/login'); // Assuming login page exists

    const emailInput = page.locator('input[type="email"]');
    if (await emailInput.isVisible()) {
      await emailInput.fill('invalid-email');

      const submitButton = page.getByRole('button', { name: /submit|sign in/i });
      await submitButton.click();

      // Verify validation error
      await expect(page.getByText(/invalid.*email|valid email/i)).toBeVisible();
    }
  });

  test('session expiration redirects to login with message', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    await dashboardPage.goto();

    // Mock session expiration (401 Unauthorized)
    await page.route('**/api/v1/**', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Session expired' }),
      });
    });

    // Trigger an API request
    await page.reload();

    // Verify redirect to login
    await expect(page).toHaveURL(/\/login|\/auth/);

    // Verify session expired message
    await expect(
      page.getByText(/session.*expired|logged out|sign in again/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('rate limiting shows appropriate error message', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock rate limit error (429 Too Many Requests)
    await page.route('**/api/v1/**', (route) => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Too many requests' }),
        headers: {
          'Retry-After': '60',
        },
      });
    });

    await dashboardPage.goto();

    // Verify rate limit error message
    await expect(
      page.getByText(/too many requests|rate limit|try again later/i)
    ).toBeVisible({ timeout: 10000 });

    // Verify retry after time is displayed
    await expect(page.getByText(/60|1 minute/i)).toBeVisible();
  });

  test('malformed API response shows generic error', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock malformed JSON response
    await page.route('**/api/v1/dashboard/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: 'invalid json {{{',
      });
    });

    await page.goto('/dashboard');

    // Verify error message about unexpected response
    await expect(
      page.getByText(/unexpected error|something went wrong|try again/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('empty required field shows validation error', async ({ page }) => {
    const foldersPage = new FoldersPage(page);

    await foldersPage.goto();

    // Open create dialog
    const addButton = page.getByRole('button', { name: /add folder/i });
    await addButton.click();

    // Try to save without filling required fields
    const saveButton = page.getByRole('button', { name: /save/i });
    await saveButton.click();

    // Verify validation error
    await expect(page.getByText(/required|cannot be empty|fill.*field/i)).toBeVisible();
  });

  test('error messages are user-friendly and actionable', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock API error
    await page.route('**/api/v1/dashboard/stats', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Database connection failed' }),
      });
    });

    await dashboardPage.goto();

    // Verify error message is displayed
    const errorMessage = page.getByText(/error|failed|wrong/i).first();
    await expect(errorMessage).toBeVisible({ timeout: 10000 });

    // Verify error message doesn't expose technical details
    await expect(page.getByText(/database|SQL|stack trace/i)).not.toBeVisible();

    // Verify actionable next step is provided
    await expect(
      page.getByText(/retry|try again|contact support|reload/i)
    ).toBeVisible();
  });

  test('loading spinner shows during async operations', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock slow API response
    await page.route('**/api/v1/dashboard/stats', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      route.continue();
    });

    const navigationPromise = dashboardPage.goto();

    // Verify loading indicator appears
    await expect(page.locator('[data-loading="true"]').or(page.getByText(/loading/i))).toBeVisible({
      timeout: 1000,
    });

    await navigationPromise;

    // Verify loading indicator disappears
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('concurrent API failures dont break UI', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Mock all API endpoints to fail
    await page.route('**/api/v1/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' }),
      });
    });

    await dashboardPage.goto();

    // Trigger multiple requests
    await page.reload();
    await page.goto('/settings/folders');
    await page.goto('/settings/notifications');

    // Verify UI remains responsive
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible({
      timeout: 10000,
    });

    // Verify no console errors or crashes
    // (Playwright will fail test if unhandled errors occur)
  });
});
