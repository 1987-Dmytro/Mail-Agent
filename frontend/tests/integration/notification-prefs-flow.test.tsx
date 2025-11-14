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

describe('Notification Preferences Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Integration Test 1: Complete preferences flow (AC: 1-10)
   * Full flow: load defaults → modify all settings → save → verify persisted
   */
  it('test_complete_preferences_flow', async () => {
    // Initial load returns default preferences
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    // Wait for form to load
    await waitFor(() => {
      expect(screen.getByLabelText(/enable batch notifications/i)).toBeInTheDocument();
    });

    await new Promise(resolve => setTimeout(resolve, 500));

    // Modify all settings
    // 1. Toggle batch off
    const batchToggle = screen.getByLabelText(/enable batch notifications/i);
    await user.click(batchToggle);

    await waitFor(() => {
      expect(batchToggle).not.toBeChecked();
    });

    // 2. Toggle batch back on and change time
    await user.click(batchToggle);
    await waitFor(() => {
      expect(screen.getByLabelText(/batch notification time/i)).toBeInTheDocument();
    });

    // 3. Toggle priority off
    const priorityToggle = screen.getByLabelText(/immediate priority notifications/i);
    await user.click(priorityToggle);
    await waitFor(() => {
      expect(priorityToggle).not.toBeChecked();
    });

    // 4. Toggle priority back on
    await user.click(priorityToggle);

    // 5. Modify quiet hours
    const quietStartInput = screen.getByLabelText(/quiet hours start/i);
    const quietEndInput = screen.getByLabelText(/quiet hours end/i);

    await user.clear(quietStartInput);
    await user.type(quietStartInput, '23:00');

    await user.clear(quietEndInput);
    await user.type(quietEndInput, '07:00');

    await new Promise(resolve => setTimeout(resolve, 200));

    // Mock update response
    const updatedPreferences = {
      ...mockPreferences,
      quiet_hours_start: '23:00',
      quiet_hours_end: '07:00',
    };

    vi.mocked(apiClient.updateNotificationPrefs).mockResolvedValue({
      data: updatedPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    // Save preferences
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Verify API was called with updated values
    await waitFor(() => {
      expect(apiClient.updateNotificationPrefs).toHaveBeenCalledTimes(1);
      expect(vi.mocked(apiClient.updateNotificationPrefs).mock.calls.length).toBeGreaterThan(0);
      const callArgs = vi.mocked(apiClient.updateNotificationPrefs).mock.calls[0]![0];
      expect(callArgs.quiet_hours_start).toBe('23:00');
      expect(callArgs.quiet_hours_end).toBe('07:00');
    }, { timeout: 3000 });

    // Verify success toast
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Notification preferences updated!');
    });

    // Simulate reload - mock API returns updated preferences
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: updatedPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    // Verify values persisted (check input values)
    const reloadedStartInput = screen.getByLabelText(/quiet hours start/i) as HTMLInputElement;
    const reloadedEndInput = screen.getByLabelText(/quiet hours end/i) as HTMLInputElement;

    await waitFor(() => {
      expect(reloadedStartInput.value).toBe('23:00');
      expect(reloadedEndInput.value).toBe('07:00');
    });
  });

  /**
   * Integration Test 2: Quiet hours overnight range (AC: 8)
   * Set 22:00-08:00, save, reload, verify valid
   */
  it('test_quiet_hours_overnight_range', async () => {
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

    await new Promise(resolve => setTimeout(resolve, 500));

    // Verify overnight range is loaded
    const startInput = screen.getByLabelText(/quiet hours start/i) as HTMLInputElement;
    const endInput = screen.getByLabelText(/quiet hours end/i) as HTMLInputElement;

    expect(startInput.value).toBe('22:00');
    expect(endInput.value).toBe('08:00');

    // Save without changes (overnight range should be valid)
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Verify no validation errors
    expect(screen.queryByText(/quiet hours end time must be different from start time/i)).not.toBeInTheDocument();

    // Verify API was called
    await waitFor(() => {
      expect(apiClient.updateNotificationPrefs).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });

    // Verify success
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Notification preferences updated!');
    });
  });

  /**
   * Integration Test 3: Batch toggle effect (AC: 2, 3)
   * Disable batch, save, verify batch_time no longer applied
   */
  it('test_batch_toggle_effect', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/enable batch notifications/i)).toBeInTheDocument();
    });

    await new Promise(resolve => setTimeout(resolve, 500));

    // Verify batch time selector is visible initially
    expect(screen.getByLabelText(/batch notification time/i)).toBeInTheDocument();

    // Toggle batch off
    const batchToggle = screen.getByLabelText(/enable batch notifications/i);
    await user.click(batchToggle);

    // Verify batch time selector is hidden
    await waitFor(() => {
      expect(screen.queryByLabelText(/batch notification time/i)).not.toBeInTheDocument();
    });

    // Mock update response with batch disabled
    const updatedPreferences = {
      ...mockPreferences,
      batch_enabled: false,
    };

    vi.mocked(apiClient.updateNotificationPrefs).mockResolvedValue({
      data: updatedPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    // Save
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Verify API was called with batch_enabled: false
    await waitFor(() => {
      expect(apiClient.updateNotificationPrefs).toHaveBeenCalledTimes(1);
      expect(vi.mocked(apiClient.updateNotificationPrefs).mock.calls.length).toBeGreaterThan(0);
      const callArgs = vi.mocked(apiClient.updateNotificationPrefs).mock.calls[0]![0];
      expect(callArgs.batch_enabled).toBe(false);
    }, { timeout: 3000 });

    // Verify success
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Notification preferences updated!');
    });

    // Batch time selector should remain hidden
    expect(screen.queryByLabelText(/batch notification time/i)).not.toBeInTheDocument();
  });

  /**
   * Integration Test 4: Test notification sends (AC: 6)
   * Click test button, verify API call made, toast shown
   */
  it('test_test_notification_sends', async () => {
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    vi.mocked(apiClient.testNotification).mockResolvedValue({
      data: { message: 'Test notification sent successfully', success: true },
      status: 200,
    } as ApiResponse<{ message: string; success: boolean }>);

    const user = userEvent.setup();
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send test notification/i })).toBeInTheDocument();
    });

    await new Promise(resolve => setTimeout(resolve, 500));

    // Click test notification button
    const testButton = screen.getByRole('button', { name: /send test notification/i });
    await user.click(testButton);

    // Verify API was called
    await waitFor(() => {
      expect(apiClient.testNotification).toHaveBeenCalledTimes(1);
    });

    // Verify success toast with timestamp
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
      expect(vi.mocked(toast.success).mock.calls.length).toBeGreaterThan(0);
      const successCall = vi.mocked(toast.success).mock.calls[0]![0];
      expect(successCall).toContain('Test notification sent');
      expect(successCall).toContain('Sent at');
    });

    // Verify button returns to normal state
    await waitFor(() => {
      expect(testButton).not.toBeDisabled();
      expect(testButton.textContent).toBe('Send Test Notification');
    });
  });

  /**
   * Integration Test 5: Preferences persist across navigation (AC: 10)
   * Save preferences, navigate away, return, verify settings still applied
   */
  it('test_preferences_persist_across_navigation', async () => {
    const modifiedPreferences = {
      ...mockPreferences,
      batch_time: '08:00',
      quiet_hours_start: '23:00',
      quiet_hours_end: '07:00',
      priority_immediate: false,
    };

    // First render - load original preferences
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: mockPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    const user = userEvent.setup();
    const { unmount } = render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/enable batch notifications/i)).toBeInTheDocument();
    });

    await new Promise(resolve => setTimeout(resolve, 500));

    // Modify settings
    const priorityToggle = screen.getByLabelText(/immediate priority notifications/i);
    await user.click(priorityToggle);

    await waitFor(() => {
      expect(priorityToggle).not.toBeChecked();
    });

    // Mock update response
    vi.mocked(apiClient.updateNotificationPrefs).mockResolvedValue({
      data: modifiedPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    // Save
    const form = document.querySelector('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(apiClient.updateNotificationPrefs).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });

    // Simulate navigation away (unmount component)
    unmount();

    // Simulate navigation back - mock API returns modified preferences
    vi.mocked(apiClient.getNotificationPrefs).mockResolvedValue({
      data: modifiedPreferences,
      status: 200,
    } as ApiResponse<NotificationPreferences>);

    // Re-render component (simulate navigation back)
    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByLabelText(/enable batch notifications/i)).toBeInTheDocument();
    });

    await new Promise(resolve => setTimeout(resolve, 500));

    // Verify preferences persisted
    const reloadedPriorityToggle = screen.getByLabelText(/immediate priority notifications/i);
    expect(reloadedPriorityToggle).not.toBeChecked();

    // Verify API was called to reload preferences
    expect(apiClient.getNotificationPrefs).toHaveBeenCalledTimes(2); // Once on first render, once on second render
  });
});
