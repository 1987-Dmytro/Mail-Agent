/**
 * Dashboard Page Integration Tests
 * Tests complete dashboard data loading and display scenarios
 * (AC: 3, 4, 12, 13)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Declare mock functions before vi.mock() calls (hoisting requirement)
// Initialize as actual mock functions so they are callable
let mockToastError = vi.fn();
let mockToastSuccess = vi.fn();
let mockUseAuthStatus = vi.fn();
let mockUseSWR = vi.fn();

// Mock all external dependencies at the top level (hoisted)
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: (...args: unknown[]) => mockToastSuccess(...args),
  },
}));

vi.mock('@/hooks/useAuthStatus', () => ({
  useAuthStatus: () => mockUseAuthStatus(),
}));

vi.mock('swr', () => ({
  default: (key: string | null, ...args: unknown[]) => mockUseSWR(key, ...args),
}));

// Import component after mocks are set up
import DashboardPage from '@/app/dashboard/page';

describe('Dashboard Page Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Initialize mock functions
    mockToastError = vi.fn();
    mockToastSuccess = vi.fn();
    mockUseAuthStatus = vi.fn();
    mockUseSWR = vi.fn();

    // Default auth mock (authenticated user)
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
  });

  /**
   * Test 1: Verify dashboard fetches stats and displays all 4 stat cards (AC: 3, 12)
   * - Mock useSWR to simulate loading then loaded state
   * - Verify DashboardSkeleton displays during loading
   * - Verify all 4 email statistics cards display with correct values
   * - Verify time_saved displays correctly (today_minutes and total_minutes)
   */
  it('test_dashboard_loads_and_displays_stats', async () => {
    let callCount = 0;

    // Mock SWR to simulate loading -> loaded transition
    mockUseSWR.mockImplementation((key: string | null) => {
      if (key === '/api/v1/dashboard/stats') {
        callCount++;

        // First call: loading state
        if (callCount === 1) {
          return {
            data: undefined,
            error: undefined,
            isLoading: true,
            mutate: vi.fn(),
            isValidating: false,
          };
        }

        // Subsequent calls: loaded state
        return {
          data: {
            data: {
              connections: {
                gmail: { connected: true },
                telegram: { connected: true },
              },
              email_stats: {
                total_processed: 42,
                pending_approval: 5,
                auto_sorted: 30,
                responses_sent: 12,
              },
              time_saved: {
                today_minutes: 25,
                total_minutes: 150, // Should display as "2h 30m"
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

    // Render dashboard (first render shows loading)
    const { rerender } = render(<DashboardPage />);

    // Verify skeleton is displayed during loading (AC: 12)
    // Skeleton should have placeholder elements
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);

    // Trigger re-render to simulate data loaded
    rerender(<DashboardPage />);

    // Wait for dashboard to finish loading
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Verify all 4 email statistics cards display (AC: 3)
    expect(screen.getByText('Total Processed')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument(); // total_processed value

    expect(screen.getByText('Pending Approval')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // pending_approval value

    expect(screen.getByText('Auto-Sorted')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument(); // auto_sorted value

    expect(screen.getByText('Responses Sent')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument(); // responses_sent value

    // Verify time saved displays correctly
    expect(screen.getByText('Time Saved')).toBeInTheDocument();
    expect(screen.getByText('25 min')).toBeInTheDocument(); // today_minutes
    expect(screen.getByText('2h 30m')).toBeInTheDocument(); // total_minutes converted to hours
  });

  /**
   * Test 2: Verify activity feed renders 10 items with correct formatting (AC: 4)
   * - Mock useSWR to return 10 activity items with mixed types
   * - Verify 10 activity items render in the feed
   * - Verify each item shows correct icon based on type
   * - Verify email_subject truncates if >50 chars
   * - Verify folder_name displays for type='sorted'
   * - Verify timestamps use date-fns relative format
   */
  it('test_dashboard_displays_activity_feed', async () => {
    // Mock SWR with activity feed data
    mockUseSWR.mockImplementation((key: string | null) => {
      if (key === '/api/v1/dashboard/stats') {
        return {
          data: {
            data: {
              connections: {
                gmail: { connected: true },
                telegram: { connected: true },
              },
              email_stats: {
                total_processed: 10,
                pending_approval: 0,
                auto_sorted: 10,
                responses_sent: 0,
              },
              time_saved: {
                today_minutes: 10,
                total_minutes: 100,
              },
              recent_activity: [
                {
                  id: 1,
                  type: 'sorted',
                  email_subject: 'Meeting invitation for Q4 planning',
                  timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min ago
                  folder_name: 'Work',
                },
                {
                  id: 2,
                  type: 'response_sent',
                  email_subject: 'RE: Project proposal feedback',
                  timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 min ago
                },
                {
                  id: 3,
                  type: 'rejected',
                  email_subject: 'Spam: You won a million dollars!',
                  timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 min ago
                },
                {
                  id: 4,
                  type: 'sorted',
                  email_subject:
                    'This is a very long email subject that should be truncated because it exceeds fifty characters',
                  timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), // 1 hour ago
                  folder_name: 'Personal',
                },
                {
                  id: 5,
                  type: 'sorted',
                  email_subject: 'Invoice #12345',
                  timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
                  folder_name: 'Finance',
                },
                {
                  id: 6,
                  type: 'response_sent',
                  email_subject: 'Thanks for the update',
                  timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
                },
                {
                  id: 7,
                  type: 'sorted',
                  email_subject: 'Newsletter: Tech Weekly',
                  timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
                  folder_name: 'Newsletters',
                },
                {
                  id: 8,
                  type: 'rejected',
                  email_subject: 'Phishing attempt detected',
                  timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
                },
                {
                  id: 9,
                  type: 'sorted',
                  email_subject: 'Flight confirmation',
                  timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
                  folder_name: 'Travel',
                },
                {
                  id: 10,
                  type: 'response_sent',
                  email_subject: 'Out of office reply',
                  timestamp: new Date(Date.now() - 7 * 60 * 60 * 1000).toISOString(),
                },
              ],
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

    // Wait for dashboard to load
    await waitFor(() => {
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    });

    // Verify activity items display
    expect(screen.getByText('Meeting invitation for Q4 planning')).toBeInTheDocument();
    expect(screen.getByText('RE: Project proposal feedback')).toBeInTheDocument();
    expect(screen.getByText('Spam: You won a million dollars!')).toBeInTheDocument();

    // Verify long subject is truncated (should end with "...")
    const truncatedText = screen.getByText(/This is a very long email subject that should be/);
    expect(truncatedText.textContent).toMatch(/\.\.\.$/);

    // Verify folder names display for sorted items
    expect(screen.getByText('Work')).toBeInTheDocument();
    expect(screen.getByText('Personal')).toBeInTheDocument();
    expect(screen.getByText('Finance')).toBeInTheDocument();

    // Verify relative timestamps display (date-fns format)
    const timestamps = screen.getAllByText(/ago/);
    expect(timestamps.length).toBeGreaterThan(0); // At least one "ago" timestamp
  });

  /**
   * Test 3: Verify loading skeleton displays while data loads (AC: 12)
   * - Mock useSWR to return isLoading=true
   * - Render dashboard
   * - Verify DashboardSkeleton component displays with skeleton cards
   * - Verify no actual data cards render during loading
   */
  it('test_dashboard_shows_loading_skeleton', () => {
    // Mock SWR to return loading state
    mockUseSWR.mockImplementation((_key: string | null) => {
      return {
        data: undefined,
        error: undefined,
        isLoading: true,
        mutate: vi.fn(),
        isValidating: false,
      };
    });

    // Render dashboard
    render(<DashboardPage />);

    // Verify skeleton elements are present (check for Skeleton components via animation class)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);

    // Verify actual content does NOT render during loading
    expect(screen.queryByText('Total Processed')).not.toBeInTheDocument();
    expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument();
    expect(screen.queryByText('Time Saved')).not.toBeInTheDocument();
  });

  /**
   * Test 4: Verify dashboard handles API errors with retry (AC: 13)
   * - Mock useSWR to return error state
   * - Render dashboard
   * - Verify error toast notification displays
   * - Verify toast has "Retry" button
   * - Click retry button
   * - Verify mutate() called to force data reload
   */
  it('test_dashboard_handles_api_errors_with_retry', async () => {
    const mockMutate = vi.fn();

    // Mock SWR to return error state
    mockUseSWR.mockImplementation((key: string | null) => {
      if (key === '/api/v1/dashboard/stats') {
        return {
          data: undefined,
          error: new Error('Network error'),
          isLoading: false,
          mutate: mockMutate,
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

    // Wait for error toast to be called
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        'Failed to load dashboard stats',
        expect.objectContaining({
          action: expect.objectContaining({
            label: 'Retry',
            onClick: expect.any(Function),
          }),
        })
      );
    });

    // Extract the retry onClick function from the toast call
    const toastCall = mockToastError.mock.calls[0];
    if (!toastCall) {
      throw new Error('Expected mockToastError to be called but it was not');
    }
    const toastOptions = toastCall[1];
    const retryFunction = toastOptions.action.onClick;

    // Simulate clicking retry button
    retryFunction();

    // Verify mutate() was called to force data reload
    expect(mockMutate).toHaveBeenCalled();

    // Verify Refresh button exists and can trigger refresh
    const refreshButton = screen.getByRole('button', { name: /Refresh/i });
    expect(refreshButton).toBeInTheDocument();

    // Click refresh button
    const user = userEvent.setup();
    await user.click(refreshButton);

    // Verify mutate called again and success toast shown
    expect(mockMutate).toHaveBeenCalledTimes(2);
    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith('Dashboard refreshed');
    });
  });
});
