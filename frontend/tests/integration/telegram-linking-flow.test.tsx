import { describe, it, expect, beforeEach, vi } from 'vitest';
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
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: mockPush,
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
 * Integration tests for Telegram Linking Flow
 *
 * Test Coverage (5 integration tests mapped to ACs):
 * 1. test_complete_telegram_linking_flow (AC: 1-7)
 * 2. test_copy_code_to_clipboard (AC: 4)
 * 3. test_code_expiration_timeout (AC: 8)
 * 4. test_connection_persists_on_refresh (AC: 6-7)
 * 5. test_network_error_retry (AC: 9)
 */

describe('Telegram Linking Flow - Integration Tests', () => {
  beforeEach(async () => {
    // Clear all mocks
    vi.clearAllMocks();

    // Reset useTelegramStatus mock to default (not linked)
    const { useTelegramStatus } = await import('@/hooks/useTelegramStatus');
    vi.mocked(useTelegramStatus).mockReturnValue({
      isLinked: false,
      isLoading: false,
      error: null,
      telegramUsername: null,
      telegramId: null,
      refresh: vi.fn(),
    });

    // Mock clipboard API using vi.spyOn
    if (!navigator.clipboard) {
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: vi.fn().mockResolvedValue(undefined),
        },
        writable: true,
        configurable: true,
      });
    }
    vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);

    // Mock window.open
    vi.spyOn(window, 'open').mockImplementation(() => null);

    // Get mocked apiClient
    const { apiClient } = await import('@/lib/api-client');

    // Set up default mocks for all apiClient methods
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'ABC123',
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        verified: false,
      },
      status: 200,
    });

    vi.mocked(apiClient.verifyTelegramLink).mockResolvedValue({
      data: {
        verified: false,
      },
      status: 200,
    });

    vi.mocked(apiClient.telegramStatus).mockResolvedValue({
      data: {
        linked: false,
      },
      status: 200,
    });
  });

  /**
   * Test 1: Complete Telegram linking flow (AC: 1-7)
   *
   * Simulates full Telegram linking flow:
   * 1. Component mounts and generates linking code
   * 2. User sees instructions and code displayed
   * 3. User copies code to clipboard
   * 4. User opens Telegram app via deep link
   * 5. User sends /start command with code in Telegram
   * 6. Backend polling detects verification
   * 7. Success state shows Telegram username
   */
  it('test_complete_telegram_linking_flow', { timeout: 20000 }, async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('@/lib/api-client');

    // Step 1: Mock successful code generation
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'XYZ789',
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        verified: false,
      },
      status: 200,
    });

    // Step 2: Mock verification polling (not verified initially)
    let verifyCallCount = 0;
    vi.mocked(apiClient.verifyTelegramLink).mockImplementation(() => {
      verifyCallCount++;
      // First 2 calls: not verified (simulating polling)
      // Third call: verified (user completed /start in Telegram)
      if (verifyCallCount <= 2) {
        return Promise.resolve({
          data: {
            verified: false,
          },
          status: 200,
        });
      } else {
        return Promise.resolve({
          data: {
            verified: true,
            telegram_id: '987654321',
            telegram_username: '@integration_test_user',
          },
          status: 200,
        });
      }
    });

    // Render component
    render(<TelegramLink />);

    // Step 3: Wait for code generation and display
    await waitFor(() => {
      expect(screen.getByText('XYZ789')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Step 4: Verify instructions are displayed (AC: 1-2)
    expect(screen.getByText('Follow these steps:')).toBeInTheDocument();
    expect(screen.getByText('Open Telegram on your device')).toBeInTheDocument();
    expect(screen.getAllByText(/@MailAgentBot/).length).toBeGreaterThan(0);
    expect(screen.getByText(/\/start XYZ789/)).toBeInTheDocument();

    // Step 5: Verify code is displayed prominently (AC: 3)
    expect(screen.getByText(/Your linking code:/)).toBeInTheDocument();
    expect(screen.getByText('XYZ789')).toBeInTheDocument();

    // Step 6: Verify "Copy Code" button is available (AC: 4)
    const copyButton = screen.getByRole('button', { name: /Copy Code/i });
    expect(copyButton).toBeEnabled();
    // Note: Clipboard functionality is tested in test_copy_code_to_clipboard

    // Step 7: Test "Open Telegram" deep link button (AC: 5)
    const telegramButton = screen.getByRole('button', { name: /Open Telegram/i });
    expect(telegramButton).toBeEnabled();
    await user.click(telegramButton);

    // Verify deep link was constructed correctly
    expect(window.open).toHaveBeenCalledWith(
      'tg://resolve?domain=mailagentbot&start=XYZ789',
      '_blank'
    );

    // Step 8: Verify polling started (AC: 6)
    await waitFor(() => {
      expect(apiClient.verifyTelegramLink).toHaveBeenCalledWith('XYZ789');
    }, { timeout: 10000 });

    // Step 9: Wait for verification success (AC: 7)
    // Polling should detect verification after 3rd call (6-9 seconds)
    await waitFor(() => {
      expect(screen.getByText('Telegram Connected!')).toBeInTheDocument();
      expect(screen.getByText(/@integration_test_user/)).toBeInTheDocument();
    }, { timeout: 15000 });

    // Step 10: Verify success state elements
    expect(screen.getByRole('button', { name: /Continue to Dashboard/i })).toBeEnabled();

    // Step 11: Verify polling stopped after success
    const callCountBeforeDelay = verifyCallCount;
    await new Promise(resolve => setTimeout(resolve, 4000)); // Wait 4 seconds
    // Call count should not increase significantly (maybe +1 for race condition)
    expect(verifyCallCount).toBeLessThanOrEqual(callCountBeforeDelay + 1);
  });

  /**
   * Test 2: Copy code to clipboard integration (AC: 4)
   *
   * Verifies clipboard API integration with toast notifications
   */
  it('test_copy_code_to_clipboard', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('@/lib/api-client');

    // Mock code generation
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'CLIP01',
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        verified: false,
      },
      status: 200,
    });

    render(<TelegramLink />);

    // Wait for code to be displayed
    await waitFor(() => {
      expect(screen.getByText('CLIP01')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Click "Copy Code" button
    const copyButton = screen.getByRole('button', { name: /Copy Code/i });
    await user.click(copyButton);

    // Verify clipboard.writeText was called with correct code
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('CLIP01');
    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);

    // Test clipboard permission error handling
    vi.mocked(navigator.clipboard.writeText).mockRejectedValueOnce(
      new Error('Clipboard permission denied')
    );

    await user.click(copyButton);

    // Component should handle error gracefully (no crash)
    expect(screen.getByText('CLIP01')).toBeInTheDocument();
  });

  /**
   * Test 3: Code expiration timeout (AC: 8)
   *
   * Verifies that expired codes show error state with "Generate New Code" option
   */
  it('test_code_expiration_timeout', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('@/lib/api-client');

    // Mock code generation with very short expiration (2 seconds)
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'EXPIRE',
        expires_at: new Date(Date.now() + 2000).toISOString(), // Expires in 2 seconds
        verified: false,
      },
      status: 200,
    });

    render(<TelegramLink />);

    // Wait for code to be displayed
    await waitFor(() => {
      expect(screen.getByText('EXPIRE')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify countdown timer is shown
    expect(screen.getByText(/Expires in/)).toBeInTheDocument();

    // Wait for code to expire (2 seconds + buffer)
    await waitFor(() => {
      // After expiration, should show error state
      const hasExpiredTime = screen.queryByText('0:00');
      const hasExpiredError = screen.queryByText(/code has expired/i);
      expect(hasExpiredTime || hasExpiredError).toBeTruthy();
    }, { timeout: 5000 });

    // Verify "Generate New Code" button appears
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate New Code/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    // Mock new code generation
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'NEWCOD',
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        verified: false,
      },
      status: 200,
    });

    // Click "Generate New Code" button
    const generateButton = screen.getByRole('button', { name: /Generate New Code/i });
    await user.click(generateButton);

    // Verify new code is generated and displayed
    await waitFor(() => {
      expect(screen.getByText('NEWCOD')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify back in polling state (not error state)
    expect(screen.queryByText(/expired/i)).not.toBeInTheDocument();
  });

  /**
   * Test 4: Connection persists on refresh (AC: 6-7)
   *
   * Verifies that linked users stay linked after page refresh
   */
  it('test_connection_persists_on_refresh', async () => {
    const { useTelegramStatus } = await import('@/hooks/useTelegramStatus');
    const { apiClient } = await import('@/lib/api-client');

    // Mock already linked user in Telegram status hook
    vi.mocked(useTelegramStatus).mockReturnValue({
      isLinked: true,
      isLoading: false,
      error: null,
      telegramUsername: '@persistent_user',
      telegramId: '123456789',
      refresh: vi.fn(),
    });

    // Mock Telegram status API (already connected)
    vi.mocked(apiClient.telegramStatus).mockResolvedValue({
      data: {
        linked: true,
        telegram_id: '123456789',
        telegram_username: '@persistent_user',
      },
      status: 200,
    });

    render(<TelegramLink />);

    // Wait for auth status check to complete
    await waitFor(() => {
      // Should skip code generation and go directly to success state
      expect(screen.getByText(/Telegram Connected!/i)).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify username is displayed
    expect(screen.getByText(/@persistent_user/)).toBeInTheDocument();

    // Verify "Continue to Dashboard" button is enabled
    expect(screen.getByRole('button', { name: /Continue to Dashboard/i })).toBeEnabled();

    // Verify code generation was NOT called (skipped due to existing connection)
    expect(apiClient.generateTelegramLink).not.toHaveBeenCalled();
  });

  /**
   * Test 5: Network error with retry (AC: 9)
   *
   * Verifies error handling for network failures with retry functionality
   */
  it('test_network_error_retry', { timeout: 15000 }, async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('@/lib/api-client');

    // Mock network error on code generation
    const networkError = Object.assign(
      new Error('Network error'),
      { status: 0, code: 'NETWORK_ERROR' }
    );

    vi.mocked(apiClient.generateTelegramLink).mockRejectedValueOnce(networkError);

    render(<TelegramLink />);

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText(/Cannot generate linking code/i)).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify error alert
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Verify "Try Again" button
    const retryButton = screen.getByRole('button', { name: /Try Again/i });
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).toBeEnabled();

    // Mock successful response for retry
    vi.mocked(apiClient.generateTelegramLink).mockResolvedValue({
      data: {
        code: 'RETRY1',
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        verified: false,
      },
      status: 200,
    });

    // Click "Try Again" button
    await user.click(retryButton);

    // Wait for successful retry
    await waitFor(() => {
      expect(screen.getByText('RETRY1')).toBeInTheDocument();
    }, { timeout: 10000 });

    // Verify back to initial/polling state (ready to use)
    expect(screen.getByText(/Follow these steps:/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy Code/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Open Telegram/i })).toBeEnabled();

    // Verify error is cleared
    expect(screen.queryByText(/Cannot generate linking code/i)).not.toBeInTheDocument();
  });
});
