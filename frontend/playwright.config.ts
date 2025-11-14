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

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI for stability
  workers: process.env.CI ? 1 : undefined,

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

    // Video on failure
    video: 'retain-on-failure',

    // Maximum time each action can take (30s)
    actionTimeout: 30000,
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
    timeout: 120000, // 2 minutes to start dev server
  },

  // Global timeout for each test (2 minutes)
  timeout: 120000,

  // Expect timeout for assertions (10 seconds)
  expect: {
    timeout: 10000,
  },
});
