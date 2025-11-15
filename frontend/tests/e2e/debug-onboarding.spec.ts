import { test, expect } from '@playwright/test';
import {
  setupAuthenticatedSession,
  mockAuthEndpoints,
  mockGmailOAuthFlow,
  mockTelegramLinkingFlow,
  mockUnauthenticatedUser,
} from './fixtures/auth';
import { mockAllApiEndpoints } from './fixtures/data';

/**
 * DEBUG TEST: Diagnose why Welcome → Gmail transition fails
 *
 * This test captures browser console logs to identify:
 * - React errors
 * - State update issues
 * - JavaScript exceptions
 * - Network errors
 */
test.describe('Onboarding Debug Tests', () => {
  test('debug Welcome to Gmail transition with console logging', async ({ page }) => {
    // Capture ALL browser console messages
    const consoleMessages: string[] = [];
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      const text = `[${msg.type()}] ${msg.text()}`;
      consoleMessages.push(text);

      if (msg.type() === 'error' || msg.type() === 'warning') {
        consoleErrors.push(text);
      }
    });

    // Capture page errors
    page.on('pageerror', (error) => {
      consoleErrors.push(`[PAGE ERROR] ${error.message}\n${error.stack}`);
    });

    // Set up mocking FIRST
    await mockAuthEndpoints(page, mockUnauthenticatedUser);
    await mockGmailOAuthFlow(page);
    await mockTelegramLinkingFlow(page);
    await mockAllApiEndpoints(page);

    // THEN set up authenticated session
    await setupAuthenticatedSession(page, mockUnauthenticatedUser);

    console.log('\n=== NAVIGATING TO ONBOARDING ===');
    await page.goto('/onboarding');
    await expect(page).toHaveURL('/onboarding');

    console.log('\n=== WAITING FOR WELCOME PAGE ===');
    await expect(page.getByText(/Welcome to Mail Agent/i)).toBeVisible({ timeout: 10000 });

    console.log('\n=== WELCOME PAGE LOADED ===');
    console.log('Console messages so far:', consoleMessages.length);
    console.log('Console errors so far:', consoleErrors.length);

    // Take screenshot BEFORE clicking
    await page.screenshot({ path: 'test-results/debug-before-click.png' });

    console.log('\n=== CLICKING GET STARTED BUTTON ===');
    const getStartedButton = page.getByRole('button', { name: /get started/i });
    await expect(getStartedButton).toBeVisible();

    // Log current step state via JavaScript
    const stepBefore = await page.evaluate(() => {
      return {
        html: document.body.innerHTML.substring(0, 500),
        localStorage: localStorage.getItem('onboarding_progress'),
      };
    });
    console.log('\n=== STATE BEFORE CLICK ===');
    console.log('localStorage:', stepBefore.localStorage);

    await getStartedButton.click();
    console.log('✓ Button clicked');

    // Wait a moment for state update
    await page.waitForTimeout(1000);

    // Take screenshot AFTER clicking
    await page.screenshot({ path: 'test-results/debug-after-click.png' });

    // Check state after click
    const stepAfter = await page.evaluate(() => {
      return {
        localStorage: localStorage.getItem('onboarding_progress'),
        currentStepText: document.body.textContent?.includes('Connect Gmail'),
      };
    });
    console.log('\n=== STATE AFTER CLICK ===');
    console.log('localStorage:', stepAfter.localStorage);
    console.log('Gmail text visible:', stepAfter.currentStepText);

    console.log('\n=== WAITING FOR GMAIL BUTTON (10s timeout) ===');
    try {
      await expect(page.getByRole('button', { name: /connect gmail/i })).toBeVisible({ timeout: 10000 });
      console.log('✓ Gmail button appeared!');
    } catch {
      console.log('✗ Gmail button DID NOT appear after 10 seconds');

      // Dump final state
      const finalState = await page.evaluate(() => {
        return {
          url: window.location.href,
          localStorage: localStorage.getItem('onboarding_progress'),
          bodyText: document.body.textContent?.substring(0, 1000),
        };
      });
      console.log('\n=== FINAL STATE ===');
      console.log('URL:', finalState.url);
      console.log('localStorage:', finalState.localStorage);
      console.log('Body text:', finalState.bodyText);

      // Take final screenshot
      await page.screenshot({ path: 'test-results/debug-final.png' });
    }

    // Print all console messages
    console.log('\n=== ALL BROWSER CONSOLE MESSAGES ===');
    consoleMessages.forEach((msg, idx) => {
      console.log(`${idx + 1}. ${msg}`);
    });

    // Print console errors/warnings
    if (consoleErrors.length > 0) {
      console.log('\n=== BROWSER CONSOLE ERRORS/WARNINGS ===');
      consoleErrors.forEach((msg, idx) => {
        console.log(`${idx + 1}. ${msg}`);
      });
    } else {
      console.log('\n✓ No console errors or warnings');
    }

    // Force test to fail for diagnostic purposes
    expect(consoleErrors.length).toBe(0);
  });
});
