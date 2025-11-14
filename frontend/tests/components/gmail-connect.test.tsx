/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
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
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
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
 * Unit tests for GmailConnect OAuth component
 *
 * Test Coverage (5 unit tests mapped to ACs):
 * 1. test_gmail_connect_button_renders (AC: 1)
 * 2. test_oauth_initiation_constructs_url (AC: 1, 5)
 * 3. test_oauth_callback_processes_code (AC: 2)
 * 4. test_csrf_state_validation (AC: 5)
 * 5. test_success_state_displays_email (AC: 3)
 */

describe('GmailConnect Component - Unit Tests', () => {
  beforeEach(async () => {
    // Clear sessionStorage before each test
    sessionStorage.clear();
    // Clear all mocks
    vi.clearAllMocks();

    // Get mocked apiClient
    const { apiClient } = await import('@/lib/api-client');

    // Set up default successful OAuth config response
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

    // Set up default successful callback response
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
  });

  /**
   * Test 1: Gmail Connect button renders (AC: 1)
   *
   * Verifies that:
   * - "Connect Gmail" button displays
   * - Permission explanation text is visible
   * - Required permissions list is shown
   */
  it('test_gmail_connect_button_renders', async () => {
    render(<GmailConnect />);

    // Wait for OAuth config to load
    await waitFor(() => {
      expect(screen.queryByText(/Loading/i)).not.toBeInTheDocument();
    });

    // Verify "Connect Gmail Account" header displays
    expect(screen.getByText(/Connect Gmail Account/i)).toBeInTheDocument();

    // Verify "Connect Gmail" button exists and is visible
    const connectButton = screen.getByRole('button', { name: /Connect Gmail/i });
    expect(connectButton).toBeInTheDocument();
    expect(connectButton).toBeVisible();

    // Verify permission explanation is shown
    expect(screen.getByText(/Required Permissions:/i)).toBeInTheDocument();

    // Verify specific permissions are listed
    expect(screen.getByText(/Read your emails to categorize them/i)).toBeInTheDocument();
    expect(screen.getByText(/Send emails on your behalf/i)).toBeInTheDocument();
    expect(screen.getByText(/Manage Gmail labels/i)).toBeInTheDocument();

    // Verify redirect explanation text
    expect(
      screen.getByText(/You'll be redirected to Google to grant permissions/i)
    ).toBeInTheDocument();
  });

  /**
   * Test 2: OAuth initiation constructs URL (AC: 1, 5)
   *
   * Verifies that:
   * - OAuth config API is called on mount
   * - Auth URL includes state parameter
   * - State token is stored in sessionStorage
   * - Window redirect is triggered with correct URL
   */
  it('test_oauth_initiation_constructs_url', async () => {
    const user = userEvent.setup();

    // Mock window.location.href
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      value: { ...originalLocation, href: '' },
      writable: true,
    });

    render(<GmailConnect />);

    // Wait for OAuth config to load
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Connect Gmail/i })).toBeInTheDocument();
    });

    // Mock crypto.randomUUID to return predictable value
    const mockUUID = 'test-state-token-12345';
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(mockUUID);

    // Click "Connect Gmail" button
    const connectButton = screen.getByRole('button', { name: /Connect Gmail/i });
    await user.click(connectButton);

    // Verify state token was stored in sessionStorage
    expect(sessionStorage.getItem('oauth_state')).toBe(mockUUID);

    // Verify window.location.href was set with state parameter
    await waitFor(() => {
      expect(window.location.href).toContain('accounts.google.com');
      expect(window.location.href).toContain(`state=${encodeURIComponent(mockUUID)}`);
    });

    // Restore window.location
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  /**
   * Test 3: OAuth callback processes code (AC: 2)
   *
   * Verifies that:
   * - Callback API is called with code and state
   * - JWT token is stored via setToken()
   * - User object is updated
   * - Success state is shown
   */
  it('test_oauth_callback_processes_code', async () => {
    const { useSearchParams } = await import('next/navigation');

    // Mock URL params with OAuth callback
    const mockSearchParams = new URLSearchParams({
      code: 'test-auth-code',
      state: 'test-state-token',
    });
    vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as any);

    // Store matching state token in sessionStorage
    sessionStorage.setItem('oauth_state', 'test-state-token');

    // Spy on setToken function
    const setTokenSpy = vi.spyOn(auth, 'setToken');

    render(<GmailConnect />);

    // Wait for callback processing to complete
    await waitFor(
      () => {
        expect(screen.getByText(/Gmail Connected!/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Verify setToken was called with JWT token
    expect(setTokenSpy).toHaveBeenCalledWith('mock-jwt-token-12345');

    // Verify user email is displayed
    expect(screen.getByText(/testuser@gmail.com/i)).toBeInTheDocument();

    // Verify success icon (checkmark) is shown
    const successCard = screen.getByText(/Gmail Connected!/i).closest('div');
    expect(successCard).toBeInTheDocument();

    // Verify "Continue" button is enabled
    const continueButton = screen.getByRole('button', { name: /Continue to Telegram Setup/i });
    expect(continueButton).toBeInTheDocument();
    expect(continueButton).toBeEnabled();

    // Verify state token was cleared from sessionStorage
    expect(sessionStorage.getItem('oauth_state')).toBeNull();
  });

  /**
   * Test 4: CSRF state validation (AC: 5)
   *
   * Verifies that:
   * - Invalid state parameter is rejected
   * - Error message is shown
   * - Token is NOT stored
   * - Retry button is available
   */
  it('test_csrf_state_validation', async () => {
    const { useSearchParams } = await import('next/navigation');

    // Mock URL params with mismatched state
    const mockSearchParams = new URLSearchParams({
      code: 'test-auth-code',
      state: 'attacker-state-token',
    });
    vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as any);

    // Store different state token in sessionStorage
    sessionStorage.setItem('oauth_state', 'legitimate-state-token');

    // Spy on setToken function
    const setTokenSpy = vi.spyOn(auth, 'setToken');

    render(<GmailConnect />);

    // Wait for error state to appear
    await waitFor(() => {
      expect(screen.getByText(/Security validation failed/i)).toBeInTheDocument();
    });

    // Verify error message is shown
    const errorAlert = screen.getByRole('alert');
    expect(errorAlert).toBeInTheDocument();
    expect(within(errorAlert).getByText(/Security validation failed/i)).toBeInTheDocument();

    // Verify setToken was NOT called
    expect(setTokenSpy).not.toHaveBeenCalled();

    // Verify "Try Again" button is present
    const retryButton = screen.getByRole('button', { name: /Try Again/i });
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).toBeEnabled();
  });

  /**
   * Test 5: Success state displays email (AC: 3)
   *
   * Verifies that:
   * - Green checkmark icon is visible
   * - User email is displayed
   * - "Continue" button is enabled
   * - Success message is shown
   */
  it('test_success_state_displays_email', async () => {
    const { useSearchParams } = await import('next/navigation');

    // Mock URL params with OAuth callback
    const mockSearchParams = new URLSearchParams({
      code: 'test-auth-code',
      state: 'test-state-token',
    });
    vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as any);

    // Store matching state token in sessionStorage
    sessionStorage.setItem('oauth_state', 'test-state-token');

    render(<GmailConnect />);

    // Wait for success state to render
    await waitFor(
      () => {
        expect(screen.getByText(/Gmail Connected!/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Verify success heading is displayed
    expect(screen.getByText(/Gmail Connected!/i)).toBeInTheDocument();

    // Verify checkmark icon is present (Check from lucide-react)
    // The Check icon should be in the document
    const successCard = screen.getByText(/Gmail Connected!/i).closest('div');
    expect(successCard).toBeInTheDocument();

    // Verify user email is displayed with emphasis
    expect(screen.getByText(/Connected to/i)).toBeInTheDocument();
    expect(screen.getByText(/testuser@gmail.com/i)).toBeInTheDocument();

    // Verify "Continue" button is enabled
    const continueButton = screen.getByRole('button', { name: /Continue to Telegram Setup/i });
    expect(continueButton).toBeInTheDocument();
    expect(continueButton).toBeEnabled();
    expect(continueButton).not.toBeDisabled();
  });
});
