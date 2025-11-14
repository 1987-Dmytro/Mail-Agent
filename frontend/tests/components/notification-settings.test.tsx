import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import NotificationSettings from '@/components/settings/NotificationSettings';
import { apiClient } from '@/lib/api-client';
import type { ApiResponse } from '@/types/api';
import type { NotificationPreferences } from '@/types/settings';

// Mock API client
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    getNotificationPrefs: vi.fn(),
    updateNotificationPrefs: vi.fn(),
    testNotification: vi.fn(),
  },
}));

// Mock toast notifications
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Sample notification preferences data
const mockPreferences: NotificationPreferences = {
  id: 1,
  user_id: 1,
  batch_enabled: true,
  batch_time: '18:00',
  quiet_hours_enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  priority_immediate: true,
  min_confidence_threshold: 0.7,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

describe('NotificationSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Test 1: Notification form renders with defaults (AC: 1, 9)
   */
  it('test_notification_form_renders_with_defaults', async () => {
    // Mock API to return preferences
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    render(<NotificationSettings />);

    // Wait for preferences to load
    await waitFor(() => {
      expect(screen.getByText('Batch Notifications')).toBeInTheDocument();
    });

    // Verify all sections are rendered
    expect(screen.getByText('Batch Notifications')).toBeInTheDocument();
    expect(screen.getByText('Priority Notifications')).toBeInTheDocument();
    expect(screen.getByText('Quiet Hours')).toBeInTheDocument();

    // Verify form controls are present
    expect(screen.getByLabelText(/enable batch notifications/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/immediate priority notifications/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/enable quiet hours/i)).toBeInTheDocument();

    // Verify action buttons are present
    expect(screen.getByRole('button', { name: /send test notification/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save preferences/i })).toBeInTheDocument();

    // Verify default values are loaded
    const batchToggle = screen.getByLabelText(/enable batch notifications/i);
    expect(batchToggle).toBeChecked();
  });

  /**
   * Test 2: Batch toggle shows/hides time selector (AC: 2, 3)
   */
  it('test_batch_toggle_shows_hides_time_selector', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/enable batch notifications/i)).toBeInTheDocument();
    });

    // Batch time selector should be visible when batch enabled
    expect(screen.getByLabelText(/batch notification time/i)).toBeInTheDocument();

    // Toggle batch off
    const batchToggle = screen.getByLabelText(/enable batch notifications/i);
    await user.click(batchToggle);

    // Batch time selector should be hidden
    await waitFor(() => {
      expect(screen.queryByLabelText(/batch notification time/i)).not.toBeInTheDocument();
    });

    // Toggle batch back on
    await user.click(batchToggle);

    // Batch time selector should be visible again
    await waitFor(() => {
      expect(screen.getByLabelText(/batch notification time/i)).toBeInTheDocument();
    });
  });

  /**
   * Test 3: Priority toggle enables/disables (AC: 4)
   */
  it('test_priority_toggle_enables_disables', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/immediate priority notifications/i)).toBeInTheDocument();
    });

    const priorityToggle = screen.getByLabelText(/immediate priority notifications/i);

    // Priority toggle should be checked initially
    expect(priorityToggle).toBeChecked();

    // Confidence threshold should be visible when priority enabled
    expect(screen.getByLabelText(/minimum confidence for priority detection/i)).toBeInTheDocument();

    // Toggle priority off
    await user.click(priorityToggle);

    // Warning should appear
    await waitFor(() => {
      expect(screen.getByText(/all emails will wait for batch/i)).toBeInTheDocument();
    });

    // Confidence threshold should be hidden
    expect(screen.queryByLabelText(/minimum confidence for priority detection/i)).not.toBeInTheDocument();

    // Toggle priority back on
    await user.click(priorityToggle);

    // Warning should disappear, confidence threshold should appear
    await waitFor(() => {
      expect(screen.queryByText(/all emails will wait for batch/i)).not.toBeInTheDocument();
      expect(screen.getByLabelText(/minimum confidence for priority detection/i)).toBeInTheDocument();
    });
  });

  /**
   * Test 4: Quiet hours validation (AC: 5, 8)
   */
  it('test_quiet_hours_validation', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/quiet hours start/i)).toBeInTheDocument();
    });

    // Wait for form to be fully initialized
    await new Promise(resolve => setTimeout(resolve, 500));

    // Set invalid quiet hours (same start and end time)
    const startInput = screen.getByLabelText(/quiet hours start/i);
    const endInput = screen.getByLabelText(/quiet hours end/i);

    await user.clear(startInput);
    await user.type(startInput, '10:00');

    await user.clear(endInput);
    await user.type(endInput, '10:00');

    // Wait for validation to register
    await new Promise(resolve => setTimeout(resolve, 200));

    // Submit form to trigger validation
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Wait for validation error to appear
    await waitFor(() => {
      expect(screen.getByText(/quiet hours end time must be different from start time/i)).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  /**
   * Test 5: Save preferences success (AC: 7, 10)
   */
  it('test_save_preferences_success', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const updatedPreferences = { ...mockPreferences, batch_time: '08:00' };
    vi.mocked(apiClient.updateNotificationPrefs).mockResolvedValue({
      data: updatedPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/batch notification time/i)).toBeInTheDocument();
    });

    // Wait longer for form to be fully initialized and react-hook-form to be ready
    await new Promise(resolve => setTimeout(resolve, 500));

    // Submit form directly instead of clicking button
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Verify API was called
    await waitFor(() => {
      expect(apiClient.updateNotificationPrefs).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });

    // Verify success toast was shown
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Notification preferences updated!');
    });
  });

  /**
   * Test 6: Test notification button (AC: 6)
   */
  it('test_test_notification_button', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    vi.mocked(apiClient.testNotification).mockResolvedValue({
      data: { message: 'Test notification sent', success: true },
      status: 200,
    } as ApiResponse<{ message: string; success: boolean }>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send test notification/i })).toBeInTheDocument();
    });

    // Click test notification button
    const testButton = screen.getByRole('button', { name: /send test notification/i });
    await user.click(testButton);

    // Verify API was called
    await waitFor(() => {
      expect(apiClient.testNotification).toHaveBeenCalledTimes(1);
    });

    // Verify success toast was shown with timestamp
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
      expect(vi.mocked(toast.success).mock.calls.length).toBeGreaterThan(0);
      const successCall = vi.mocked(toast.success).mock.calls[0]![0];
      expect(successCall).toContain('Test notification sent');
      expect(successCall).toContain('Sent at');
    });
  });

  /**
   * Test 7: Form disables during submit (AC: 7)
   */
  it('test_form_disables_during_submit', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    // Mock slow API response
    vi.mocked(apiClient.updateNotificationPrefs).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        data: mockPreferences,
        status: 200,
      } as ApiResponse<NotificationPreferences>), 300))
    );

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save preferences/i })).toBeInTheDocument();
    });

    // Wait for form to be fully initialized
    await new Promise(resolve => setTimeout(resolve, 500));

    const saveButton = screen.getByRole('button', { name: /save preferences/i });
    const testButton = screen.getByRole('button', { name: /send test notification/i });

    // Submit form
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Wait briefly for state update
    await new Promise(resolve => setTimeout(resolve, 50));

    // Check that both buttons are disabled
    await waitFor(() => {
      expect(saveButton).toBeDisabled();
      expect(testButton).toBeDisabled();
    });

    // Wait for API call to complete
    await waitFor(() => {
      expect(saveButton).not.toBeDisabled();
    }, { timeout: 1000 });
  });

  /**
   * Test 8: Overnight quiet hours valid (AC: 8)
   */
  it('test_overnight_quiet_hours_valid', async () => {
    // Mock preferences with overnight quiet hours (22:00 - 08:00)
    const overnightPreferences = {
      ...mockPreferences,
      quiet_hours_start: '22:00',
      quiet_hours_end: '08:00',
    };

    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: overnightPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    vi.mocked(apiClient.updateNotificationPrefs).mockResolvedValue({
      data: overnightPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/quiet hours start/i)).toBeInTheDocument();
    });

    // Verify overnight range is loaded correctly
    const startInput = screen.getByLabelText(/quiet hours start/i) as HTMLInputElement;
    const endInput = screen.getByLabelText(/quiet hours end/i) as HTMLInputElement;

    expect(startInput.value).toBe('22:00');
    expect(endInput.value).toBe('08:00');

    // Wait for form to be fully initialized
    await new Promise(resolve => setTimeout(resolve, 500));

    // Submit form - should succeed without validation errors
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Verify no validation errors
    await waitFor(() => {
      expect(screen.queryByText(/quiet hours end time must be different from start time/i)).not.toBeInTheDocument();
    });

    // Verify API was called (no validation blocked the submission)
    await waitFor(() => {
      expect(apiClient.updateNotificationPrefs).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });

    // Verify success toast
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Notification preferences updated!');
    });
  });
});
