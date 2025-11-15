import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Mail Agent Frontend E2E Tests
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Test Coverage:
 * - Complete onboarding flow (4-step wizard)
 * - Dashboard data loading and display
 * - Folder CRUD operations
 * - Notification preferences updates
 * - Error handling scenarios
 *
 * Browser Coverage: Chromium, Firefox, WebKit (Safari)
 * Target: ≥95% pass rate over 10 consecutive runs
 * Execution Time Target: <5 minutes total
 */
export default defineConfig({
  // Test directory
  testDir: './tests/e2e',

  // Ignore debug tests on CI
  testIgnore: process.env.CI ? '**/debug-*.spec.ts' : undefined,

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only - reduced to 1 for faster feedback
  retries: process.env.CI ? 1 : 0,

  // Use 2 workers on CI for faster execution while maintaining stability
  workers: process.env.CI ? 2 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
    ...(process.env.CI ? [['github'] as const] : [])
  ],

  // Shared settings for all tests
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: 'http://localhost:3000',

    // Collect trace on first retry
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure - disabled on CI to save time
    video: process.env.CI ? 'off' : 'retain-on-failure',

    // Maximum time each action can take - reduced for CI speed
    actionTimeout: process.env.CI ? 15000 : 30000, // 15s on CI, 30s locally
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
    },

    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 },
      },
    },

    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1280, height: 720 },
      },
    },

    // Mobile testing
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
      },
    },

    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 12'],
      },
    },
  ],

  // Run your local dev server before starting the tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60000, // 1 minute to start dev server (optimized for CI)
  },

  // Global timeout for each test - reduced for CI speed
  timeout: process.env.CI ? 60000 : 120000, // 1 minute on CI, 2 minutes locally

  // Expect timeout for assertions (10 seconds)
  expect: {
    timeout: 10000,
  },
});
