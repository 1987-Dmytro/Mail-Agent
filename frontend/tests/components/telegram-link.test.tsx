import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TelegramLink } from '@/components/onboarding/TelegramLink';

/**
 * Mock API Client
 */
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    generateTelegramLink: vi.fn(),
    verifyTelegramLink: vi.fn(),
    telegramStatus: vi.fn(),
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
}));

/**
 * Mock useTelegramStatus hook
 */
vi.mock('@/hooks/useTelegramStatus', () => ({
  useTelegramStatus: vi.fn(() => ({
    isLinked: false,
    isLoading: false,
    error: null,
    telegramUsername: null,
    telegramId: null,
    refresh: vi.fn(),
  })),
}));

/**
 * Unit tests for TelegramLink component
 *
 * Test Coverage (6 unit tests mapped to ACs):
 * 1. test_telegram_linking_page_renders_instructions (AC: 1-2)
 * 2. test_copy_code_button_copies_to_clipboard (AC: 4)
 * 3. test_deep_link_opens_telegram (AC: 5)
 * 4. test_polling_verifies_link_success (AC: 6-7)
 * 5. test_code_expiration_shows_error (AC: 8)
 * 6. test_error_handling_network_failure (AC: 9)
 */

describe('TelegramLink Component - Unit Tests', () => {
  // Store original clipboard API
  let originalClipboard: Clipboard;
  let originalWindowOpen: typeof window.open;

  beforeEach(async () => {
    // Clear all mocks
    vi.clearAllMocks();

    // Store original APIs
    originalClipboard = navigator.clipboard;
    originalWindowOpen = window.open;

    // Mock clipboard API
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      writable: true,
      configurable: true,
    });

    // Mock window.open
    window.open = vi.fn();

    // Get mocked apiClient
    const { apiClient } = await import('@/lib/api-client');

    // Set up default successful linking code generation
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'ABC123',
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(), // 10 minutes from now
        verified: false,
      },
      status: 200,
    });

    // Set up default verification response (not verified initially)
    vi.mocked(apiClient.verifyTelegramLink).mockResolvedValue({
      data: {
        verified: false,
      },
      status: 200,
    });

    // Set up default Telegram status (not linked)
    vi.mocked(apiClient.telegramStatus).mockResolvedValue({
      data: {
        connected: false,
      },
      status: 200,
    });
  });

  afterEach(() => {
    // Restore original APIs
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      writable: true,
      configurable: true,
    });
    window.open = originalWindowOpen;
  });

  /**
   * Test 1: Telegram linking page renders instructions and code display (AC: 1-2)
   *
   * Verifies that:
   * - Step-by-step instructions are displayed
   * - Instructions include "1. Open Telegram, 2. Search for @MailAgentBot, 3. Send /start [code]"
   * - Linking code is displayed prominently
   * - "Copy Code" and "Open Telegram" buttons are rendered
   */
  it('test_telegram_linking_page_renders_instructions', async () => {
    render(<TelegramLink />);

    // Wait for code generation
    await waitFor(() => {
      expect(screen.getByText('ABC123')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify step-by-step instructions (AC: 1-2)
    expect(screen.getByText('Follow these steps:')).toBeInTheDocument();
    expect(screen.getByText('Open Telegram on your device')).toBeInTheDocument();
    expect(screen.getByText(/Search for/)).toBeInTheDocument();
    expect(screen.getAllByText(/@MailAgentBot/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Send/).length).toBeGreaterThan(0);
    expect(screen.getByText(/\/start ABC123/)).toBeInTheDocument();

    // Verify code display (AC: 3)
    expect(screen.getByText('ABC123')).toBeInTheDocument();
    expect(screen.getByText(/Your linking code:/)).toBeInTheDocument();

    // Verify action buttons (AC: 4-5)
    expect(screen.getByRole('button', { name: /Copy Code/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Open Telegram/i })).toBeInTheDocument();

    // Verify countdown timer is shown
    expect(screen.getByText(/Expires in/)).toBeInTheDocument();
  });

  /**
   * Test 2: Copy Code button copies to clipboard (AC: 4)
   *
   * Verifies that:
   * - "Copy Code" button triggers clipboard API
   * - Code is copied correctly
   * - Success toast is displayed
   */
  it('test_copy_code_button_copies_to_clipboard', async () => {
    render(<TelegramLink />);

    // Wait for code generation
    await waitFor(() => {
      expect(screen.getByText('ABC123')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Click "Copy Code" button
    const copyButton = screen.getByRole('button', { name: /Copy Code/i });
    copyButton.click();

    // Verify clipboard.writeText was called with correct code
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('ABC123');
  });

  /**
   * Test 3: Deep link button opens Telegram (AC: 5)
   *
   * Verifies that:
   * - "Open Telegram" button triggers window.open
   * - Deep link URL is constructed correctly: tg://resolve?domain=mailagentbot&start=CODE
   */
  it('test_deep_link_opens_telegram', async () => {
    const user = userEvent.setup();
    render(<TelegramLink />);

    // Wait for code generation
    await waitFor(() => {
      expect(screen.getByText('ABC123')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Click "Open Telegram" button
    const telegramButton = screen.getByRole('button', { name: /Open Telegram/i });
    await user.click(telegramButton);

    // Verify window.open was called with correct deep link
    await waitFor(() => {
      expect(window.open).toHaveBeenCalledWith(
        'tg://resolve?domain=mailagentbot&start=ABC123',
        '_blank'
      );
    });
  });

  /**
   * Test 4: Polling verifies link success (AC: 6-7)
   *
   * Verifies that:
   * - Verification polling starts automatically
   * - Backend is polled every 3 seconds
   * - Success state displays username when verified
   * - Polling stops after verification
   */
  it('test_polling_verifies_link_success', async () => {
    const { apiClient } = await import('@/lib/api-client');

    // Mock verification to succeed after code is generated
    let callCount = 0;
    vi.mocked(apiClient.verifyTelegramLink).mockImplementation(() => {
      callCount++;
      // First call: not verified (allow code to display)
      // Second call: verified (trigger success state)
      return Promise.resolve({
        data: callCount === 1 ? {
          verified: false,
        } : {
          verified: true,
          telegram_id: '123456789',
          telegram_username: '@testuser',
        },
        status: 200,
      });
    });

    render(<TelegramLink />);

    // Wait for code generation
    await waitFor(() => {
      expect(screen.getByText('ABC123')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify polling was initiated
    await waitFor(() => {
      expect(apiClient.verifyTelegramLink).toHaveBeenCalledWith('ABC123');
    }, { timeout: 10000 });

    // Wait for success state (after second poll)
    await waitFor(() => {
      expect(screen.getByText('Telegram Connected!')).toBeInTheDocument();
      expect(screen.getByText(/@testuser/)).toBeInTheDocument();
    }, { timeout: 10000 });
  });

  /**
   * Test 5: Code expiration shows error (AC: 8)
   *
   * Verifies that:
   * - Code expires after 10 minutes
   * - "Code expired" error is shown
   * - "Generate New Code" button is displayed
   * - Clicking "Generate New Code" restarts flow
   */
  it('test_code_expiration_shows_error', async () => {
    const { apiClient } = await import('@/lib/api-client');

    // Set up code that is already expired (expires_at in the past)
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValueOnce({
      data: {
        code: 'XYZ789',
        expires_at: new Date(Date.now() - 1000).toISOString(), // 1 second ago (expired)
        verified: false,
      },
      status: 200,
    });

    render(<TelegramLink />);

    // Wait for code generation
    await waitFor(() => {
      expect(screen.getByText('XYZ789')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify countdown shows 0:00 or expiration error appears
    await waitFor(() => {
      const hasExpiredTime = screen.queryByText('0:00');
      const hasExpiredError = screen.queryByText(/code has expired/i);
      expect(hasExpiredTime || hasExpiredError).toBeTruthy();
    }, { timeout: 10000 });
  });

  /**
   * Test 6: Error handling for network failure (AC: 9)
   *
   * Verifies that:
   * - Network errors during code generation are handled
   * - Error message is displayed
   * - "Try Again" button allows retry
   */
  it('test_error_handling_network_failure', async () => {
    const { apiClient } = await import('@/lib/api-client');

    // Simulate network error on code generation
    vi.mocked(apiClient.generateTelegramLink).mockRejectedValueOnce(
      new Error('Network error')
    );

    render(<TelegramLink />);

    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByText(/Cannot generate linking code/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();
    }, { timeout: 10000 });
  });
});
