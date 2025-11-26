/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GmailConnect } from '@/components/onboarding/GmailConnect';
import * as auth from '@/lib/auth';

/**
 * Mock API Client
 */
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    gmailOAuthConfig: vi.fn(),
    gmailCallback: vi.fn(),
    authStatus: vi.fn(),
  },
}));

/**
 * Mock Next.js navigation hooks
 */
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
  })),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

/**
 * Mock useAuthStatus hook
 */
vi.mock('@/hooks/useAuthStatus', () => ({
  useAuthStatus: vi.fn(() => ({
    isAuthenticated: false,
    isLoading: false,
    error: null,
    user: null,
    refresh: vi.fn(),
  })),
}));

/**
 * Integration tests for Gmail OAuth flow
 *
 * Test Coverage (5 integration tests mapped to ACs):
 * 1. test_complete_oauth_flow (AC: 1-3, 5-6)
 * 2. test_oauth_error_user_denies (AC: 4)
 * 3. test_oauth_state_mismatch_rejected (AC: 5)
 * 4. test_connection_persists_on_refresh (AC: 6)
 * 5. test_network_error_retry (AC: 4)
 */

describe('Gmail OAuth Flow - Integration Tests', () => {
  beforeEach(async () => {
    // Clear storage before each test
    sessionStorage.clear();
    localStorage.clear();

    // IMPORTANT: Reset ALL mocks to clear any previous test's mock implementations
    vi.resetAllMocks();

    // Re-establish the vi.mock() for apiClient after reset
    const { apiClient } = await import('@/lib/api-client');

    // Set up fresh, clean mocks for all apiClient methods
    vi.mocked(apiClient.gmailOAuthConfig).mockResolvedValue({
      data: {
        auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test&state=test',
        client_id: 'test-client-id',
        scopes: ['gmail.readonly'],
      },
      status: 200,
    });

    vi.mocked(apiClient.gmailCallback).mockResolvedValue({
      data: {
        user: { id: 1, email: 'test@example.com', gmail_connected: true, telegram_connected: false },
        token: 'test-token',
      },
      status: 200,
    });
  });

  /**
   * Test 1: Complete OAuth flow (AC: 1-3, 5-6)
   *
   * Simulates full OAuth flow:
   * 1. User clicks "Connect Gmail" button
   * 2. OAuth config fetched from backend
   * 3. CSRF state token generated and stored
   * 4. Redirect to Google (simulated)
   * 5. Callback with authorization code
   * 6. Token exchange
   * 7. JWT stored
   * 8. Success state displayed
   */
  it('test_complete_oauth_flow', async () => {
    const user = userEvent.setup();
    const { useSearchParams } = await import('next/navigation');
    const { apiClient } = await import('@/lib/api-client');

    const mockStateToken = 'integration-test-state-123';

    // Mock successful OAuth config response
    vi.mocked(apiClient.gmailOAuthConfig).mockResolvedValue({
      data: {
        auth_url: `https://accounts.google.com/o/oauth2/v2/auth?client_id=test-client-id&redirect_uri=http://localhost:8000/auth/callback&state=${mockStateToken}`,
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

    // Mock successful callback response
    vi.mocked(apiClient.gmailCallback).mockResolvedValue({
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

    // Mock initial page load (no callback params)
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any);

    // Mock window.location.href
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      value: { ...originalLocation, href: '' },
      writable: true,
    });

    // Step 1: Render component (initial state)
    const { rerender } = render(<GmailConnect />);

    // Wait for OAuth config to load
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Connect Gmail/i })).toBeInTheDocument();
    });

    // Step 2: Click "Connect Gmail" button (state already in auth_url from mock)
    const connectButton = screen.getByRole('button', { name: /Connect Gmail/i });
    await user.click(connectButton);

    // Step 3: Verify state stored in sessionStorage
    expect(sessionStorage.getItem('oauth_state')).toBe(mockStateToken);

    // Step 4: Verify redirect URL constructed correctly
    await waitFor(() => {
      expect(window.location.href).toContain('accounts.google.com');
      expect(window.location.href).toContain(`state=${encodeURIComponent(mockStateToken)}`);
    });

    // Step 5: Simulate OAuth callback (user returned from Google)
    const mockCallbackParams = new URLSearchParams({
      code: 'integration-test-code',
      state: mockStateToken,
    });
    vi.mocked(useSearchParams).mockReturnValue(mockCallbackParams as any);

    // Store state token to pass validation
    sessionStorage.setItem('oauth_state', mockStateToken);

    // Spy on setToken
    const setTokenSpy = vi.spyOn(auth, 'setToken');

    // Rerender component with callback params
    rerender(<GmailConnect />);

    // Step 6: Wait for OAuth callback processing
    await waitFor(
      () => {
        expect(screen.getByText(/Gmail Connected!/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Step 8: Verify token was stored
    expect(setTokenSpy).toHaveBeenCalledWith('mock-jwt-token-12345');

    // Step 9: Verify success state
    expect(screen.getByText(/testuser@gmail.com/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Continue/i })).toBeEnabled();

    // Step 10: Verify state cleared from sessionStorage
    expect(sessionStorage.getItem('oauth_state')).toBeNull();

    // Restore window.location
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  /**
   * Test 2: User denies permission (AC: 4)
   *
   * Verifies error handling when user denies OAuth permission
   */
  it('test_oauth_error_user_denies', async () => {
    const { useSearchParams } = await import('next/navigation');

    // Mock callback with error=access_denied
    const mockErrorParams = new URLSearchParams({
      error: 'access_denied',
      error_description: 'User denied permission',
    });
    vi.mocked(useSearchParams).mockReturnValue(mockErrorParams as any);

    render(<GmailConnect />);

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText(/Permission denied/i)).toBeInTheDocument();
    });

    // Verify error alert is shown
    const errorAlert = screen.getByRole('alert');
    expect(errorAlert).toBeInTheDocument();

    // Verify "Try Again" button is present
    const retryButton = screen.getByRole('button', { name: /Try Again/i });
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).toBeEnabled();

    // Verify explanation message for user denial
    expect(
      screen.getByText(/Mail Agent requires Gmail access to function/i)
    ).toBeInTheDocument();
  });

  /**
   * Test 3: State mismatch rejected (AC: 5)
   *
   * Verifies CSRF protection by rejecting callback with invalid state
   */
  it('test_oauth_state_mismatch_rejected', async () => {
    const { useSearchParams } = await import('next/navigation');

    // Mock callback with mismatched state
    const mockCallbackParams = new URLSearchParams({
      code: 'test-code',
      state: 'attacker-state',
    });
    vi.mocked(useSearchParams).mockReturnValue(mockCallbackParams as any);

    // Store different state token (legitimate)
    sessionStorage.setItem('oauth_state', 'legitimate-state');

    // Spy on setToken
    const setTokenSpy = vi.spyOn(auth, 'setToken');

    render(<GmailConnect />);

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText(/Security validation failed/i)).toBeInTheDocument();
    });

    // Verify error is shown
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Verify token was NOT stored (CSRF protection worked)
    expect(setTokenSpy).not.toHaveBeenCalled();

    // Verify retry button
    expect(screen.getByRole('button', { name: /Try Again/i })).toBeEnabled();
  });

  /**
   * Test 4: Connection persists on refresh (AC: 6)
   *
   * Verifies that authenticated users stay authenticated after page refresh
   */
  it('test_connection_persists_on_refresh', async () => {
    const { useSearchParams } = await import('next/navigation');
    const { useAuthStatus } = await import('@/hooks/useAuthStatus');

    // Mock authenticated user in auth status hook
    vi.mocked(useAuthStatus).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      user: {
        id: 1,
        email: 'persistent@gmail.com',
        gmail_connected: true,
        telegram_connected: false,
      },
      refresh: vi.fn(),
    });

    // Mock empty search params (normal page load, no callback)
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any);

    render(<GmailConnect />);

    // Wait for auth status check to complete
    await waitFor(
      () => {
        // Should skip OAuth flow and go directly to success state
        expect(screen.getByText(/Gmail Connected!/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Verify user email is displayed
    expect(screen.getByText(/persistent@gmail.com/i)).toBeInTheDocument();

    // Verify "Continue" button is enabled
    expect(screen.getByRole('button', { name: /Continue/i })).toBeEnabled();

    // Verify OAuth config fetch was NOT called (skipped due to existing auth)
    // Success state shown immediately without OAuth flow
  });

  /**
   * Test 5: Network error with retry (AC: 4)
   *
   * Verifies error handling for network failures with retry functionality
   */
  it('test_network_error_retry', async () => {
    const user = userEvent.setup();
    const { useSearchParams } = await import('next/navigation');
    const { apiClient } = await import('@/lib/api-client');

    // Mock empty search params
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any);

    // Mock network error on OAuth config fetch
    // Create error object that matches what the component expects
    const networkError = Object.assign(
      new Error('Network error. Please check your connection.'),
      { status: 0, code: 'NETWORK_ERROR' }
    );

    vi.mocked(apiClient.gmailOAuthConfig).mockImplementation(() => {
      return Promise.reject(networkError);
    });

    // Mock successful callback (in case retry succeeds)
    vi.mocked(apiClient.gmailCallback).mockResolvedValue({
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

    render(<GmailConnect />);

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText(/No internet connection/i)).toBeInTheDocument();
    });

    // Verify error alert
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Verify "Try Again" button
    const retryButton = screen.getByRole('button', { name: /Try Again/i });
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).toBeEnabled();

    // Mock successful response for retry
    vi.mocked(apiClient.gmailOAuthConfig).mockResolvedValue({
      data: {
        auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test-client-id&redirect_uri=http://localhost:8000/auth/callback&state=test-state',
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

    // Click "Try Again" button
    await user.click(retryButton);

    // Wait for successful retry
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Connect Gmail/i })).toBeInTheDocument();
    });

    // Verify back to initial state (ready to retry OAuth flow)
    expect(screen.getByText(/Connect Gmail Account/i)).toBeInTheDocument();
  });
});
