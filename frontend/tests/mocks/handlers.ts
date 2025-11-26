import { http, HttpResponse } from 'msw';
import { mockDashboardStats } from '../e2e/fixtures/data';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * MSW request handlers for mocking API responses
 */
export const handlers = [
  // Mock health check endpoint
  http.get(`${API_URL}/health`, () => {
    return HttpResponse.json({
      data: { status: 'healthy' },
      message: 'API is running',
      status: 200,
    });
  }),

  // NOTE: Auth endpoints (/api/v1/auth/status, /api/v1/auth/me) are handled by test-specific mocks
  // See tests/e2e/fixtures/auth.ts:mockAuthEndpoints()
  // This allows tests to control auth state per-test

  // ============================================
  // User Management Endpoints
  // ============================================

  // Mock update user (used for completing onboarding)
  http.patch(`${API_URL}/api/v1/users/me`, async ({ request }) => {
    const body = await request.json() as { onboarding_completed?: boolean };
    console.log(`🔵 MSW: Intercepted PATCH ${request.url}`, body);
    return HttpResponse.json({
      data: {
        id: 'user-123',
        email: 'test@example.com',
        gmail_connected: true,
        telegram_connected: true,
        onboarding_completed: body.onboarding_completed ?? true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      status: 200,
    });
  }),

  // Mock complete onboarding endpoint
  http.post(`${API_URL}/api/v1/users/complete-onboarding`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted POST ${request.url}`);
    return HttpResponse.json({
      data: {
        success: true,
        message: 'Onboarding completed successfully',
      },
      status: 200,
    });
  }),

  // ============================================
  // Gmail OAuth Endpoints
  // ============================================

  // Mock Gmail OAuth configuration
  http.get(`${API_URL}/api/v1/auth/gmail/config`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted GET ${request.url}`);
    return HttpResponse.json({
      data: {
        auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test-client-id&redirect_uri=http://localhost:8000/auth/callback',
        client_id: 'test-client-id.apps.googleusercontent.com',
        scopes: [
          'https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.labels',
        ],
      },
      status: 200,
    });
  }),

  // Mock Gmail OAuth callback
  // FIXED: Changed from POST to GET to match actual API client implementation
  // API client sends GET request with query params: ?code=...&state=...
  http.get(`${API_URL}/api/v1/auth/gmail/callback`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted GET ${request.url}`);

    // Extract code and state from query parameters
    const url = new URL(request.url);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state');

    // Simulate state validation failure
    if (state === 'invalid-state') {
      return HttpResponse.json(
        {
          message: 'Invalid state parameter',
          code: 'INVALID_STATE',
          status: 400,
        },
        { status: 400 }
      );
    }

    // Simulate successful OAuth callback
    console.log(`🔵 MSW→PW: GET /api/v1/auth/gmail/callback → 200`);
    return HttpResponse.json({
      data: {
        user: {
          id: 1,
          email: 'testuser@gmail.com',
          gmail_connected: true,
          telegram_connected: false,
        },
        token: 'mock-jwt-token-12345',
      },
      message: 'Gmail account connected successfully',
      status: 200,
    });
  }),

  // Mock token refresh endpoint
  http.post(`${API_URL}/api/v1/auth/refresh`, () => {
    return HttpResponse.json({
      data: {
        token: 'new-refreshed-token-67890',
      },
      status: 200,
    });
  }),

  // ============================================
  // Telegram Linking Endpoints
  // ============================================

  // Mock Telegram link code generation
  http.post(`${API_URL}/api/v1/telegram/link`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted POST ${request.url}`);
    return HttpResponse.json({
      data: {
        code: '123456',
        expires_at: new Date(Date.now() + 600000).toISOString(), // 10 min from now
        verified: false,
      },
      status: 200,
    });
  }),

  // Mock Telegram link verification
  http.get(`${API_URL}/api/v1/telegram/verify/:code`, async ({ request, params }) => {
    console.log(`🔵 MSW: Intercepted GET ${request.url} (code: ${params.code})`);

    // Add 2-second delay to simulate realistic verification polling
    // This gives E2E tests time to verify initial state before success
    await new Promise(resolve => setTimeout(resolve, 2000));

    return HttpResponse.json({
      data: {
        verified: true,
        telegram_id: '123456789',
        telegram_username: 'testuser',
      },
      status: 200,
    });
  }),

  // ============================================
  // Dashboard Endpoints
  // ============================================

  // Mock dashboard stats
  // FIXED: Use correct data structure from mockDashboardStats
  http.get(`${API_URL}/api/v1/dashboard/stats`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted GET ${request.url}`);
    return HttpResponse.json({
      data: mockDashboardStats,
      status: 200,
    });
  }),

  // ============================================
  // Folder Management Endpoints
  // ============================================

  // Mock get folders
  http.get(`${API_URL}/api/v1/folders`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted GET ${request.url}`);
    return HttpResponse.json({
      data: [],
      status: 200,
    });
  }),

  // Mock create folder
  http.post(`${API_URL}/api/v1/folders`, async ({ request }) => {
    const body = await request.json() as { name: string; keywords: string; color?: string };
    console.log(`🔵 MSW: Intercepted POST ${request.url}`, body);
    return HttpResponse.json({
      data: {
        id: `folder-${Date.now()}`,
        name: body.name,
        keywords: body.keywords,
        color: body.color || '#3b82f6',
        order: 1,
        created_at: new Date().toISOString(),
      },
      status: 201,
    });
  }),

  // ============================================
  // Notification Preferences Endpoints
  // ============================================

  // Mock get notification preferences
  http.get(`${API_URL}/api/v1/notifications/preferences`, ({ request }) => {
    console.log(`🔵 MSW: Intercepted GET ${request.url}`);
    return HttpResponse.json({
      data: {
        batch_enabled: false,
        batch_time: '09:00',
        quiet_hours_enabled: false,
        quiet_hours_start: '22:00',
        quiet_hours_end: '08:00',
        priority_immediate: true,
      },
      status: 200,
    });
  }),

  // Mock update notification preferences
  http.patch(`${API_URL}/api/v1/notifications/preferences`, async ({ request }) => {
    const body = await request.json();
    console.log(`🔵 MSW: Intercepted PATCH ${request.url}`, body);
    return HttpResponse.json({
      data: body,
      status: 200,
    });
  }),
];
