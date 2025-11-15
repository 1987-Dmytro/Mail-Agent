import { Page } from '@playwright/test';

/**
 * Authentication Fixtures for E2E Tests
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Provides mock authentication utilities for testing authenticated flows
 *
 * FIXED: Updated to match actual app auth implementation
 * - Correct localStorage key: 'mail_agent_token' (not 'auth_token')
 * - Correct API endpoint: '/api/v1/auth/status' (not '/api/v1/auth/me')
 * - Valid JWT token format for decodeToken() compatibility
 * - User ID as number (not string)
 */

export interface MockUser {
  id: number;
  email: string;
  gmail_connected: boolean;
  telegram_connected: boolean;
  telegram_id?: string;
  telegram_username?: string;
  onboarding_completed?: boolean;
}

export const mockAuthenticatedUser: MockUser = {
  id: 1,
  email: 'test@example.com',
  gmail_connected: true,
  telegram_connected: true,
  telegram_id: '123456789',
  telegram_username: 'testuser',
  onboarding_completed: true,
};

export const mockUnauthenticatedUser: MockUser = {
  id: 2,
  email: 'newuser@example.com',
  gmail_connected: false,
  telegram_connected: false,
  onboarding_completed: false,
};

/**
 * Generate a valid JWT token for testing
 * Token format: header.payload.signature (Base64-encoded)
 * Expires in 24 hours (safe for test duration)
 */
function generateMockJWT(userId: number, email: string): string {
  const header = { alg: 'HS256', typ: 'JWT' };
  const payload = {
    user_id: userId,
    email: email,
    exp: Math.floor(Date.now() / 1000) + 86400, // 24 hours from now
    iat: Math.floor(Date.now() / 1000),
  };

  // Base64-encode header and payload (signature not validated in tests)
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const fakeSignature = 'test_signature_not_validated';

  return `${encodedHeader}.${encodedPayload}.${fakeSignature}`;
}

/**
 * Mock JWT token for authenticated requests
 * Valid JWT format that passes client-side decodeToken() checks
 */
export const mockAuthToken = generateMockJWT(mockAuthenticatedUser.id, mockAuthenticatedUser.email);

/**
 * Set up authenticated session by mocking localStorage/cookies
 * FIXED: Uses correct localStorage key 'mail_agent_token' to match app
 * CRITICAL FIX: Set localStorage synchronously BEFORE page navigation
 */
export async function setupAuthenticatedSession(page: Page, user: MockUser = mockAuthenticatedUser) {
  // Generate token for this user
  const token = generateMockJWT(user.id, user.email);

  // CRITICAL: Use addInitScript for ALL future page loads
  await page.addInitScript((t) => {
    localStorage.setItem('mail_agent_token', t);
  }, token);

  // ALSO set it immediately by navigating to a base page first
  // This ensures localStorage is set before navigating to protected pages
  await page.goto('/');
  await page.evaluate((t) => {
    localStorage.setItem('mail_agent_token', t);
  }, token);
}

/**
 * Mock API responses for authentication endpoints
 * FIXED: Added /api/v1/auth/status endpoint (actually used by app)
 */
export async function mockAuthEndpoints(page: Page, user: MockUser = mockAuthenticatedUser) {
  // Mock GET /api/v1/auth/status (CRITICAL: this is what useAuthStatus() calls)
  await page.route('**/api/v1/auth/status', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          authenticated: true,
          user,
        },
        status: 200,
      }),
    });
  });

  // Mock GET /api/v1/auth/me (legacy endpoint, may still be used)
  await page.route('**/api/v1/auth/me', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: user,
        status: 200,
      }),
    });
  });

  // Mock POST /api/v1/auth/logout
  await page.route('**/api/v1/auth/logout', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { message: 'Logged out successfully' },
        status: 200,
      }),
    });
  });
}

/**
 * Mock Gmail OAuth flow
 */
export async function mockGmailOAuthFlow(page: Page) {
  // Mock GET /api/v1/auth/gmail/config
  // CRITICAL FIX: Return LOCAL callback URL instead of Google OAuth URL
  // This prevents window.location.href navigation to external domain
  // GmailConnect will add state parameter and navigate to /onboarding?code=...&state=...
  await page.route('**/api/v1/auth/gmail/config', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          // Return callback URL directly (component will add state parameter)
          auth_url: '/onboarding?code=mock-code',
          client_id: 'mock-client-id',
          scopes: ['gmail.modify', 'gmail.send'],
        },
        status: 200,
      }),
    });
  });

  // CRITICAL: Mock Google OAuth redirect - prevent actual navigation to Google
  // This must be set up BEFORE clicking "Connect Gmail" button
  // OAuth callback redirects BACK TO /onboarding with code/state params
  // The GmailConnect component detects these params and processes them
  await page.route('https://accounts.google.com/o/oauth2/**', async (route) => {
    // Get the state parameter from the OAuth URL
    const url = new URL(route.request().url());
    const state = url.searchParams.get('state') || 'mock-state';

    // Instead of navigating to Google, immediately redirect back to onboarding
    // with OAuth callback params (code + state)
    await route.fulfill({
      status: 302,
      headers: {
        location: `http://localhost:3000/onboarding?code=mock-code&state=${state}`,
      },
    });
  });

  // Mock POST /api/v1/auth/gmail/callback
  // GmailConnect component expects: response.data.token and response.data.user
  await page.route('**/api/v1/auth/gmail/callback', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          user: {
            ...mockAuthenticatedUser,
            gmail_connected: true,
          },
          token: mockAuthToken,
        },
        status: 200,
      }),
    });
  });
}

/**
 * Mock Telegram linking flow
 */
export async function mockTelegramLinkingFlow(page: Page) {
  // Mock POST /api/v1/telegram/link (code generation)
  // FIXED: Match localhost:8000 (backend API baseURL)
  await page.route('**/api/v1/telegram/link', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            code: '123456',
            expires_at: new Date(Date.now() + 600000).toISOString(), // 10 min from now
            verified: false,
          },
          status: 200,
        }),
      });
    } else {
      route.continue();
    }
  });

  // Mock GET /api/v1/telegram/verify/:code (verification polling)
  // FIXED: Corrected endpoint and added ApiResponse wrapper
  await page.route('**/api/v1/telegram/verify/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          verified: true,
          telegram_id: '123456789',
          telegram_username: 'testuser',
        },
        status: 200,
      }),
    });
  });
}

/**
 * Clear authentication (logout)
 * FIXED: Uses correct localStorage key 'mail_agent_token'
 */
export async function clearAuth(page: Page) {
  await page.evaluate(() => {
    localStorage.removeItem('mail_agent_token');
    sessionStorage.removeItem('mail_agent_token');
  });
}
