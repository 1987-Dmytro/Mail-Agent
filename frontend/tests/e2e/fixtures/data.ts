/**
 * Test Data Fixtures for E2E Tests
 * Story 4.8: End-to-End Onboarding Testing and Polish
 *
 * Provides mock data for testing various components
 *
 * UPDATED: Added comprehensive API endpoint mocking functions
 */

import { Page } from '@playwright/test';

export interface FolderCategory {
  id: number;
  name: string;
  keywords: string;
  color: string;
  order: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  batch_enabled: boolean;
  batch_time: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  priority_immediate: boolean;
}

export interface DashboardStats {
  connections: {
    gmail_connected: boolean;
    telegram_connected: boolean;
    last_sync: string;
  };
  email_stats: {
    total_processed: number;
    today: number;
    this_week: number;
    needs_approval: number;
  };
  time_saved: {
    hours: number;
    minutes: number;
  };
  recent_activity: Array<{
    id: string;
    email_subject: string;
    action: string;
    timestamp: string;
    category?: string;
  }>;
}

export const mockFolderCategories: FolderCategory[] = [
  {
    id: 1,
    name: 'Government',
    keywords: 'finanzamt, tax, bürgeramt',
    color: '#3b82f6',
    order: 1,
    is_default: false,
    created_at: '2025-01-10T10:00:00Z',
    updated_at: '2025-01-10T10:00:00Z',
  },
  {
    id: 2,
    name: 'Banking',
    keywords: 'bank, sparkasse, n26',
    color: '#10b981',
    order: 2,
    is_default: false,
    created_at: '2025-01-10T10:01:00Z',
    updated_at: '2025-01-10T10:01:00Z',
  },
  {
    id: 3,
    name: 'Work',
    keywords: 'project, meeting, deadline',
    color: '#f59e0b',
    order: 3,
    is_default: false,
    created_at: '2025-01-10T10:02:00Z',
    updated_at: '2025-01-10T10:02:00Z',
  },
];

export const mockNotificationPreferences: NotificationPreferences = {
  batch_enabled: true,
  batch_time: '09:00',
  quiet_hours_enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  priority_immediate: true,
};

export const mockDashboardStats: DashboardStats = {
  connections: {
    gmail_connected: true,
    telegram_connected: true,
    last_sync: new Date().toISOString(),
  },
  email_stats: {
    total_processed: 127,
    today: 8,
    this_week: 34,
    needs_approval: 3,
  },
  time_saved: {
    hours: 2,
    minutes: 15,
  },
  recent_activity: [
    {
      id: 'activity-1',
      email_subject: 'Tax Return Documents',
      action: 'Sorted to Government',
      timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
      category: 'Government',
    },
    {
      id: 'activity-2',
      email_subject: 'Bank Statement',
      action: 'Sorted to Banking',
      timestamp: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
      category: 'Banking',
    },
    {
      id: 'activity-3',
      email_subject: 'Project Update Meeting',
      action: 'Sorted to Work',
      timestamp: new Date(Date.now() - 10800000).toISOString(), // 3 hours ago
      category: 'Work',
    },
  ],
};

/**
 * Create a new folder category for testing
 */
export function createMockFolder(overrides?: Partial<FolderCategory>): FolderCategory {
  return {
    id: Date.now(),
    name: 'Test Folder',
    keywords: 'test, example',
    color: '#8b5cf6',
    order: 99,
    is_default: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create mock notification preferences for testing
 */
export function createMockNotificationPrefs(
  overrides?: Partial<NotificationPreferences>
): NotificationPreferences {
  return {
    ...mockNotificationPreferences,
    ...overrides,
  };
}

/**
 * Mock all common API endpoints used across E2E tests
 * This is a comprehensive setup function that mocks:
 * - Dashboard stats
 * - Folder operations (GET, POST, PUT, DELETE)
 * - Notification preferences (GET, PUT)
 * - Onboarding completion
 *
 * Call this in test beforeEach hooks after setting up authentication
 *
 * @param page - Playwright page instance
 */
export async function mockAllApiEndpoints(page: Page): Promise<void> {
  // Mock Dashboard Stats Endpoint
  await page.route('**/api/v1/dashboard/stats', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        connections: {
          gmail: {
            connected: true,
            last_sync: new Date().toISOString(),
          },
          telegram: {
            connected: true,
            last_sync: new Date().toISOString(),
          },
        },
        email_stats: {
          total_processed: 127,
          pending_approval: 3,
          auto_sorted: 100,
          responses_sent: 24,
        },
        time_saved: {
          today_minutes: 45,
          total_minutes: 2340,
        },
        recent_activity: [
          {
            id: 1,
            type: 'sorted' as const,
            email_subject: 'Tax Return Documents',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            folder_name: 'Government',
          },
          {
            id: 2,
            type: 'response_sent' as const,
            email_subject: 'Bank Statement Query',
            timestamp: new Date(Date.now() - 7200000).toISOString(),
          },
        ],
      }),
    });
  });

  // Mock Folders List (GET /api/v1/folders)
  await page.route('**/api/v1/folders', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            name: 'Government',
            keywords: 'finanzamt, tax, bürgeramt',
            color: '#3b82f6',
            order: 1,
            is_default: false,
            created_at: '2025-01-10T10:00:00Z',
            updated_at: '2025-01-10T10:00:00Z',
          },
          {
            id: 2,
            name: 'Banking',
            keywords: 'bank, sparkasse, n26',
            color: '#10b981',
            order: 2,
            is_default: false,
            created_at: '2025-01-10T10:01:00Z',
            updated_at: '2025-01-10T10:01:00Z',
          },
          {
            id: 3,
            name: 'Work',
            keywords: 'project, meeting, deadline',
            color: '#f59e0b',
            order: 3,
            is_default: false,
            created_at: '2025-01-10T10:02:00Z',
            updated_at: '2025-01-10T10:02:00Z',
          },
        ]),
      });
    } else if (route.request().method() === 'POST') {
      // Create new folder
      const postData = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: Date.now(),
          ...postData,
          is_default: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });
    } else {
      await route.continue();
    }
  });

  // Mock Individual Folder Operations (PUT, DELETE /api/v1/folders/:id)
  await page.route('**/api/v1/folders/*', async (route) => {
    if (route.request().method() === 'PUT') {
      const putData = route.request().postDataJSON();
      const folderId = route.request().url().split('/').pop();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: parseInt(folderId || '1'),
          ...putData,
          updated_at: new Date().toISOString(),
        }),
      });
    } else if (route.request().method() === 'DELETE') {
      await route.fulfill({
        status: 204,
        contentType: 'application/json',
        body: '',
      });
    } else {
      await route.continue();
    }
  });

  // Mock Notification Preferences (GET /api/v1/notifications/preferences)
  await page.route('**/api/v1/notifications/preferences', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          batch_enabled: true,
          batch_time: '09:00',
          quiet_hours_enabled: true,
          quiet_hours_start: '22:00',
          quiet_hours_end: '08:00',
          priority_immediate: true,
        }),
      });
    } else if (route.request().method() === 'PUT') {
      const putData = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(putData),
      });
    } else {
      await route.continue();
    }
  });

  // Mock Test Notification Endpoint
  await page.route('**/api/v1/notifications/test', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Test notification sent successfully' }),
    });
  });

  // Mock Onboarding Completion Endpoint
  await page.route('**/api/v1/onboarding/complete', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        onboarding_completed: true,
      }),
    });
  });
}
