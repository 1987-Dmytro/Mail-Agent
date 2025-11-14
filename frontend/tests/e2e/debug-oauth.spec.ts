import { test, expect } from '@playwright/test';
import { OnboardingPage } from './pages/OnboardingPage';
import {
  setupAuthenticatedSession,
  mockAuthEndpoints,
  mockGmailOAuthFlow,
  mockUnauthenticatedUser,
} from './fixtures/auth';
import { mockAllApiEndpoints } from './fixtures/data';

/**
 * Debug test to understand OAuth navigation flow
 */
test.describe('OAuth Debug', () => {
  let onboardingPage: OnboardingPage;

  test.beforeEach(async ({ page }) => {
    await mockAuthEndpoints(page, mockUnauthenticatedUser);
    await mockGmailOAuthFlow(page);
    await mockAllApiEndpoints(page);
    await setupAuthenticatedSession(page, mockUnauthenticatedUser);

    onboardingPage = new OnboardingPage(page);

    // Listen to console messages
    page.on('console', (msg) => console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`));
  });

  test('debug OAuth flow with localStorage tracking', async ({ page }) => {
    // Step 1: Navigate to onboarding
    await onboardingPage.goto();

    const storage1 = await page.evaluate(() => localStorage.getItem('onboarding_progress'));
    console.log('=== AFTER GOTO ===');
    console.log('localStorage:', storage1);
    console.log('URL:', await page.url());

    // Step 2: Click "Get Started"
    await onboardingPage.completeWelcomeStep();

    const storage2 = await page.evaluate(() => localStorage.getItem('onboarding_progress'));
    console.log('\n=== AFTER GET STARTED ===');
    console.log('localStorage:', storage2);
    console.log('URL:', await page.url());

    // Step 3: Click "Connect Gmail"
    const connectButton = page.getByRole('button', { name: /connect gmail/i });
    await expect(connectButton).toBeVisible();

    console.log('\n=== BEFORE CONNECT CLICK ===');
    const storage3 = await page.evaluate(() => localStorage.getItem('onboarding_progress'));
    console.log('localStorage:', storage3);
    console.log('URL:', await page.url());

    // Click and wait for navigation
    await connectButton.click();

    // Wait for URL change
    await page.waitForTimeout(2000);

    console.log('\n=== AFTER CONNECT CLICK ===');
    const storage4 = await page.evaluate(() => localStorage.getItem('onboarding_progress'));
    console.log('localStorage:', storage4);
    console.log('URL:', await page.url());
    console.log('sessionStorage oauth_state:', await page.evaluate(() => sessionStorage.getItem('oauth_state')));

    // Check page content
    const welcomeVisible = await page.getByText(/Welcome to Mail Agent/i).isVisible();
    const gmailConnectedVisible = await page.getByText(/gmail connected/i).isVisible();
    console.log('Welcome visible?', welcomeVisible);
    console.log('Gmail Connected visible?', gmailConnectedVisible);

    // Fail the test so we see the output
    expect(false).toBe(true);
  });
});
