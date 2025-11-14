/**
 * Dashboard Component Unit Tests
 * Tests connection status display logic (AC: 2, 14)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock all external dependencies at the top level (hoisted)
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// Mock useAuthStatus with a default implementation
const mockUseAuthStatus = vi.fn();
vi.mock('@/hooks/useAuthStatus', () => ({
  useAuthStatus: () => mockUseAuthStatus(),
}));

// Mock SWR with a default implementation
const mockUseSWR = vi.fn();
vi.mock('swr', () => ({
  default: (key: string | null) => mockUseSWR(key),
}));

// Import component after mocks are set up
import DashboardPage from '@/app/dashboard/page';

describe('Dashboard Connection Status', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Test 1: Verify connection status displays connected state (AC: 2)
   * - Mock useAuthStatus to return authenticated user
   * - Mock useSWR to return connected=true for both Gmail and Telegram
   * - Render dashboard and verify green badges display with "Connected" text
   * - Verify last_sync time displays correctly using date-fns relative formatting
   */
  it('test_connection_status_displays_connected_state', () => {
    // Mock authenticated user
    mockUseAuthStatus.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      user: {
        id: 1,
        email: 'test@example.com',
        gmail_connected: true,
        telegram_connected: true,
        onboarding_completed: true,
      },
      refresh: vi.fn(),
    });

    // Mock SWR to return connected state
    mockUseSWR.mockImplementation((key: string | null) => {
      if (key === '/api/v1/dashboard/stats') {
        return {
          data: {
            data: {
              connections: {
                gmail: {
                  connected: true,
                  last_sync: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
                },
                telegram: {
                  connected: true,
                },
              },
              email_stats: {
                total_processed: 10,
                pending_approval: 2,
                auto_sorted: 8,
                responses_sent: 5,
              },
              time_saved: {
                today_minutes: 15,
                total_minutes: 120,
              },
              recent_activity: [],
            },
          },
          error: undefined,
          isLoading: false,
          mutate: vi.fn(),
          isValidating: false,
        };
      }
      return {
        data: undefined,
        error: undefined,
        isLoading: false,
        mutate: vi.fn(),
        isValidating: false,
      };
    });

    // Render dashboard
    render(<DashboardPage />);

    // Verify dashboard renders
    expect(screen.getByText('Dashboard')).toBeInTheDocument();

    // Verify Gmail and Telegram connections show "Connected"
    const connectedElements = screen.getAllByText('Connected');
    expect(connectedElements.length).toBe(2); // Gmail + Telegram

    // Verify green status indicators are present (check for green text classes)
    connectedElements.forEach((element) => {
      expect(element.className).toMatch(/text-green/);
    });

    // Verify last sync time is displayed for Gmail (using date-fns relative format)
    expect(screen.getByText(/Last sync:/)).toBeInTheDocument();
    expect(screen.getByText(/ago/)).toBeInTheDocument();

    // Verify "All systems operational" message
    expect(screen.getByText('All systems operational')).toBeInTheDocument();
  });

  /**
   * Test 2: Verify reconnect buttons appear when connections are disconnected (AC: 14)
   * - Mock useAuthStatus to return user with disconnected services
   * - Mock useSWR to return connected=false for both Gmail and Telegram
   * - Render dashboard and verify red badges display with "Disconnected" text
   * - Verify "Reconnect Gmail" and "Reconnect Telegram" buttons appear
   */
  it('test_connection_status_displays_reconnect_buttons', () => {
    // Mock authenticated user with disconnected services
    mockUseAuthStatus.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      user: {
        id: 1,
        email: 'test@example.com',
        gmail_connected: false,
        telegram_connected: false,
        onboarding_completed: true,
      },
      refresh: vi.fn(),
    });

    // Mock SWR to return disconnected state
    mockUseSWR.mockImplementation((key: string | null) => {
      if (key === '/api/v1/dashboard/stats') {
        return {
          data: {
            data: {
              connections: {
                gmail: {
                  connected: false,
                  error: 'Authentication expired',
                },
                telegram: {
                  connected: false,
                  error: 'Bot not linked',
                },
              },
              email_stats: {
                total_processed: 0,
                pending_approval: 0,
                auto_sorted: 0,
                responses_sent: 0,
              },
              time_saved: {
                today_minutes: 0,
                total_minutes: 0,
              },
              recent_activity: [],
            },
          },
          error: undefined,
          isLoading: false,
          mutate: vi.fn(),
          isValidating: false,
        };
      }
      return {
        data: undefined,
        error: undefined,
        isLoading: false,
        mutate: vi.fn(),
        isValidating: false,
      };
    });

    // Render dashboard
    render(<DashboardPage />);

    // Verify dashboard renders
    expect(screen.getByText('Dashboard')).toBeInTheDocument();

    // Verify Gmail and Telegram connections show "Disconnected"
    const disconnectedElements = screen.getAllByText('Disconnected');
    expect(disconnectedElements.length).toBe(2); // Gmail + Telegram

    // Verify red status indicators are present (check for red text classes)
    disconnectedElements.forEach((element) => {
      expect(element.className).toMatch(/text-red/);
    });

    // Verify "Reconnect Gmail" button appears
    const reconnectGmailButton = screen.getByRole('button', { name: /Reconnect Gmail/i });
    expect(reconnectGmailButton).toBeInTheDocument();

    // Verify "Reconnect Telegram" button appears
    const reconnectTelegramButton = screen.getByRole('button', { name: /Reconnect Telegram/i });
    expect(reconnectTelegramButton).toBeInTheDocument();

    // Verify error messages display
    expect(screen.getByText('Authentication expired')).toBeInTheDocument();
    expect(screen.getByText('Bot not linked')).toBeInTheDocument();

    // Verify "Service disruption" warning message
    expect(screen.getByText('Service disruption')).toBeInTheDocument();
  });
});
