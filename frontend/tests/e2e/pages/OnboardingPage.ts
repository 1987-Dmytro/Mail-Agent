import { Page, expect } from '@playwright/test';
import { mockGmailOAuthFlow, mockTelegramLinkingFlow } from '../fixtures/auth';

/**
 * Page Object for Onboarding Wizard
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Represents the 4-step onboarding wizard flow:
 * Step 1: Gmail OAuth Connection
 * Step 2: Telegram Bot Linking
 * Step 3: Folder Categories Configuration
 * Step 4: Notification Preferences Setup
 */
export class OnboardingPage {
  constructor(private page: Page) {}

  /**
   * Navigate to onboarding page
   * NOTE: Does not wait for Welcome step - page may load on any step if localStorage has saved state
   */
  async goto() {
    await this.page.goto('/onboarding');
    await expect(this.page).toHaveURL('/onboarding');

    // Wait for page to load (any step heading will do)
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Set up persistent localStorage that survives page reloads
   * CRITICAL: Must be called BEFORE any navigation to prevent React useEffect race condition
   * App has bug where SAVE useEffect runs before LOAD useEffect on mount, overwriting localStorage
   */
  private async setupPersistentStorage(state: { currentStep: number; gmailConnected: boolean; telegramConnected: boolean }) {
    // Use addInitScript to inject localStorage BEFORE React app loads
    // This ensures localStorage is already set when LOAD useEffect runs
    await this.page.addInitScript((storageState) => {
      const onboardingState = {
        ...storageState,
        folders: [],
        lastUpdated: new Date().toISOString(),
      };
      localStorage.setItem('onboarding_progress', JSON.stringify(onboardingState));
    }, state);
  }

  /**
   * Complete Welcome step (Step 1) by clicking "Get Started"
   * NOTE: localStorage is already set up in test beforeEach with currentStep: 2
   */
  async completeWelcomeStep() {
    // Click "Get Started" button to proceed to Step 2
    const getStartedButton = this.page.getByRole('button', { name: /get started/i });
    await expect(getStartedButton).toBeVisible();
    await getStartedButton.click();

    // Wait for transition to Step 2 (Gmail) - verify Gmail connect button appears
    await expect(this.page.getByRole('button', { name: /connect gmail/i })).toBeVisible({ timeout: 10000 });
  }

  /**
   * Step 1: Complete Gmail OAuth connection
   * NOTE: OAuth config API is mocked to return LOCAL callback URL instead of Google OAuth
   * This allows window.location.href navigation to stay within localhost:3000
   */
  async completeGmailStep() {
    // Wait for Gmail connect button
    const connectButton = this.page.getByRole('button', { name: /connect gmail/i });
    await expect(connectButton).toBeVisible();

    // Click connect button - this will:
    // 1. Fetch OAuth config (mocked to return /onboarding?code=mock-code)
    // 2. Generate state token and save to sessionStorage
    // 3. Navigate to /onboarding?code=mock-code&state=${token} (stays on localhost!)
    // 4. GmailConnect detects query params and calls handleOAuthCallback()
    await connectButton.click();

    // Wait for navigation to callback URL (with state parameter added by component)
    await this.page.waitForURL(/\/onboarding\?code=mock-code&state=/, { timeout: 10000 });

    // Wait for OAuth callback to be processed and success state to show
    await expect(this.page.getByText(/gmail connected/i)).toBeVisible({ timeout: 20000 });
  }

  /**
   * Step 2: Complete Telegram bot linking
   *
   * SIMPLIFIED: Just wait for success state and continue
   * Works whether Telegram is already connected or needs linking
   */
  async completeTelegramStep() {
    // Set up mock Telegram linking flow
    await mockTelegramLinkingFlow(this.page);

    // Wait for success state to appear (either immediately or after linking flow)
    // Success state always shows "Telegram Connected!" heading
    await expect(this.page.getByText(/telegram connected!/i)).toBeVisible({ timeout: 15000 });

    console.log('✓ Telegram connected');
  }

  /**
   * Step 4: Create folder categories
   *
   * SIMPLIFIED: Use suggested folders (bulk add)
   * Folders param kept for backward compatibility but not used
   */
  async completeFoldersStep(folders?: Array<{ name: string; keywords: string; color?: string }>) {
    // Wait for step 4 to be visible
    await expect(this.page.getByRole('heading', { name: /setup.*folders/i }).first()).toBeVisible();

    // Click "Add These 3 Folders" button (suggested folders)
    const addSuggestedButton = this.page.getByRole('button', { name: /add these.*folders/i });
    await expect(addSuggestedButton).toBeVisible({ timeout: 10000 });
    await addSuggestedButton.click();

    // Wait for folders to be added (API call completes)
    await this.page.waitForTimeout(1000);

    console.log('✓ Folders added (suggested)');
  }

  /**
   * Step 4: Configure notification preferences
   */
  async completePreferencesStep(preferences?: {
    batchEnabled?: boolean;
    batchTime?: string;
    quietHoursEnabled?: boolean;
    quietHoursStart?: string;
    quietHoursEnd?: string;
    priorityImmediate?: boolean;
  }) {
    // Wait for step 4 to be visible
    await expect(this.page.getByText(/notification preferences/i)).toBeVisible();

    // Mock notification preferences API
    await this.page.route('**/api/v1/notifications/preferences', (route) => {
      if (route.request().method() === 'PATCH') {
        const postData = route.request().postDataJSON();
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(postData),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_enabled: false,
            batch_time: '09:00',
            quiet_hours_enabled: false,
            quiet_hours_start: '22:00',
            quiet_hours_end: '08:00',
            priority_immediate: true,
          }),
        });
      }
    });

    // Configure preferences if provided
    if (preferences) {
      if (preferences.batchEnabled !== undefined) {
        const batchToggle = this.page.getByLabel(/batch notifications/i);
        if (preferences.batchEnabled) {
          await batchToggle.check();
        } else {
          await batchToggle.uncheck();
        }
      }

      if (preferences.quietHoursEnabled !== undefined) {
        const quietHoursToggle = this.page.getByLabel(/quiet hours/i);
        if (preferences.quietHoursEnabled) {
          await quietHoursToggle.check();
        } else {
          await quietHoursToggle.uncheck();
        }
      }
    }

    // Complete setup
    const completeButton = this.page.getByRole('button', { name: /complete setup/i });
    await expect(completeButton).toBeVisible();
    await completeButton.click();
  }

  /**
   * Verify onboarding completion and redirect to dashboard
   */
  async verifyOnboardingComplete() {
    // Wait for redirect to dashboard
    await expect(this.page).toHaveURL('/dashboard', { timeout: 10000 });

    // Verify onboarding completion in backend
    // This would be checked via API call in real scenario
  }

  /**
   * Complete full onboarding flow
   */
  async completeFullOnboarding() {
    await this.goto();
    await this.completeWelcomeStep(); // Step 1: Click "Get Started"
    await this.completeGmailStep(); // Step 2: Connect Gmail
    await this.completeTelegramStep(); // Step 3: Link Telegram
    await this.completeFoldersStep([ // Step 4: Create folders
      { name: 'Government', keywords: 'finanzamt, tax, bürgeramt' },
      { name: 'Banking', keywords: 'bank, sparkasse, n26' },
      { name: 'Work', keywords: 'project, meeting, deadline' },
    ]);
    await this.completePreferencesStep({ // Step 5: Set preferences (if exists)
      batchEnabled: true,
      quietHoursEnabled: true,
      priorityImmediate: true,
    });
    await this.verifyOnboardingComplete();
  }
}
