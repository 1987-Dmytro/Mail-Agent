import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@/types/api';
import { getToken, removeToken } from './auth';

/**
 * Extended Axios request config with retry tracking
 */
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  __retryCount?: number;
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Axios-based API client singleton
 * Handles authentication, retries, and error formatting
 */
class ApiClient {
  private client: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: unknown) => void;
    reject: (reason?: unknown) => void;
  }> = [];

  constructor() {
    // Initialize axios instance with base configuration
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 30000, // 30 seconds
      withCredentials: true, // For httpOnly cookies
      headers: {
        'Content-Type': 'application/json',
      },
      // In test environment, explicitly use XHR adapter for MSW compatibility
      ...(process.env.NODE_ENV === 'test' && {
        adapter: 'xhr',
      }),
    });

    // Request interceptor: Add JWT token to requests
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = getToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: Handle errors and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized (token expired)
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Queue requests while refreshing token
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            })
              .then(() => this.client(originalRequest))
              .catch((err) => Promise.reject(err));
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            // Attempt to refresh token via backend endpoint
            const response = await axios.post<ApiResponse<{ token: string }>>(
              `${this.client.defaults.baseURL}/api/v1/auth/refresh`,
              {},
              {
                withCredentials: true, // Send httpOnly refresh token cookie
              }
            );

            if (response.data.data.token) {
              // Store new access token
              const { setToken } = await import('./auth');
              setToken(response.data.data.token);

              // Update Authorization header for queued requests
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${response.data.data.token}`;
              }

              // Process queued requests
              this.failedQueue.forEach((req) => req.resolve());
              this.failedQueue = [];

              // Retry original request with new token
              return this.client(originalRequest);
            } else {
              throw new Error('No token received from refresh endpoint');
            }
          } catch (refreshError) {
            // Refresh failed - clear token and redirect to login
            removeToken();
            this.failedQueue.forEach((req) => req.reject(refreshError));
            this.failedQueue = [];

            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }

            return Promise.reject(new ApiError('Session expired', 401, 'TOKEN_EXPIRED'));
          } finally {
            this.isRefreshing = false;
          }
        }

        // Handle 403 Forbidden (insufficient permissions)
        if (error.response?.status === 403) {
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          return Promise.reject(
            new ApiError('Access forbidden', 403, 'FORBIDDEN', error.response?.data)
          );
        }

        // Handle network errors with retry logic
        if (
          !error.response &&
          error.code === 'ECONNABORTED' &&
          !(originalRequest._retry)
        ) {
          originalRequest._retry = true;

          // Exponential backoff: wait before retry
          await new Promise((resolve) => setTimeout(resolve, 1000));

          // Retry request up to 3 times
          const extendedRequest = originalRequest as ExtendedAxiosRequestConfig;
          const retryCount = extendedRequest.__retryCount || 0;
          if (retryCount < 3) {
            extendedRequest.__retryCount = retryCount + 1;
            return this.client(originalRequest);
          }
        }

        // Format error response
        const apiError = this.formatError(error);
        return Promise.reject(apiError);
      }
    );
  }

  /**
   * Format Axios errors into ApiError instances
   */
  private formatError(error: AxiosError): ApiError {
    // Debug logging for tests
    if (process.env.NODE_ENV === 'test') {
      console.error('🔴 Axios Error Details:', {
        message: error.message,
        code: error.code,
        hasResponse: !!error.response,
        hasRequest: !!error.request,
        config: error.config ? {
          url: error.config.url,
          baseURL: error.config.baseURL,
          method: error.config.method
        } : null
      });
    }

    if (error.response) {
      // Server responded with error status
      const data = error.response.data as { message?: string; code?: string; details?: unknown };
      return new ApiError(
        data.message || 'An error occurred',
        error.response.status,
        data.code,
        data.details
      );
    } else if (error.request) {
      // Request made but no response received
      return new ApiError(
        'Network error. Please check your connection.',
        0,
        'NETWORK_ERROR'
      );
    } else {
      // Error in request configuration
      return new ApiError(error.message || 'Request failed', 0, 'REQUEST_ERROR');
    }
  }

  /**
   * Generic GET request
   */
  async get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
    const response = await this.client.get<ApiResponse<T>>(url, { params });
    return response.data;
  }

  /**
   * Generic POST request
   */
  async post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
    const response = await this.client.post<ApiResponse<T>>(url, data);
    return response.data;
  }

  /**
   * Generic PUT request
   */
  async put<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
    const response = await this.client.put<ApiResponse<T>>(url, data);
    return response.data;
  }

  /**
   * Generic DELETE request
   */
  async delete<T>(url: string): Promise<ApiResponse<T>> {
    const response = await this.client.delete<ApiResponse<T>>(url);
    return response.data;
  }

  /**
   * Generic PATCH request
   */
  async patch<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
    const response = await this.client.patch<ApiResponse<T>>(url, data);
    return response.data;
  }

  // ============================================
  // OAuth & Authentication Methods
  // ============================================

  /**
   * Get Gmail OAuth configuration
   * Returns authorization URL with client_id and scopes
   */
  async gmailOAuthConfig() {
    return this.get<{
      auth_url: string;
      client_id: string;
      scopes: string[];
    }>('/api/v1/auth/gmail/config');
  }

  /**
   * Exchange OAuth authorization code for JWT token
   * @param code - Authorization code from Google OAuth callback
   * @param state - CSRF state token for validation
   */
  async gmailCallback(code: string, state: string) {
    return this.post<{
      user: {
        id: number;
        email: string;
        gmail_connected: boolean;
        telegram_connected: boolean;
      };
      token: string;
    }>('/api/v1/auth/gmail/callback', { code, state });
  }

  /**
   * Check authentication status and get current user
   * Used for connection persistence across page refreshes
   */
  async authStatus() {
    return this.get<{
      authenticated: boolean;
      user?: {
        id: number;
        email: string;
        gmail_connected: boolean;
        telegram_connected: boolean;
      };
    }>('/api/v1/auth/status');
  }

  // ============================================
  // Telegram Linking Methods
  // ============================================

  /**
   * Generate a new Telegram linking code
   * Returns 6-digit alphanumeric code with 10-minute expiration
   * User sends this code to @MailAgentBot via /start command
   */
  async generateTelegramLink() {
    return this.post<{
      code: string;
      expires_at: string;
      verified: boolean;
    }>('/api/v1/telegram/link');
  }

  /**
   * Verify if a Telegram linking code has been used
   * Called via polling mechanism (every 3 seconds) to check verification status
   * @param code - 6-digit alphanumeric linking code
   */
  async verifyTelegramLink(code: string) {
    return this.get<{
      verified: boolean;
      telegram_id?: string;
      telegram_username?: string;
    }>(`/api/v1/telegram/verify/${code}`);
  }

  /**
   * Check Telegram connection status
   * Used for connection persistence across page refreshes
   * Returns whether user has already linked their Telegram account
   */
  async telegramStatus() {
    return this.get<{
      connected: boolean;
      telegram_id?: string;
      telegram_username?: string;
    }>('/api/v1/telegram/status');
  }

  // ============================================
  // Folder Management Methods
  // ============================================

  /**
   * Get all folder categories for authenticated user
   * Returns array of FolderCategory objects
   */
  async getFolders() {
    return this.get<{
      id: number;
      user_id: number;
      name: string;
      gmail_label_id: string;
      keywords: string[];
      color: string;
      is_default: boolean;
      created_at: string;
      updated_at: string;
    }[]>('/api/v1/folders');
  }

  /**
   * Create new folder category
   * Creates Gmail label and stores folder in database
   * @param data - Folder creation payload (name, keywords?, color?)
   */
  async createFolder(data: { name: string; keywords?: string[]; color?: string }) {
    return this.post<{
      id: number;
      user_id: number;
      name: string;
      gmail_label_id: string;
      keywords: string[];
      color: string;
      is_default: boolean;
      created_at: string;
      updated_at: string;
    }>('/api/v1/folders', data);
  }

  /**
   * Update existing folder category
   * Updates Gmail label name and folder metadata
   * @param id - Folder ID
   * @param data - Folder update payload (name?, keywords?, color?, is_default?)
   */
  async updateFolder(
    id: number,
    data: { name?: string; keywords?: string[]; color?: string; is_default?: boolean }
  ) {
    return this.put<{
      id: number;
      user_id: number;
      name: string;
      gmail_label_id: string;
      keywords: string[];
      color: string;
      is_default: boolean;
      created_at: string;
      updated_at: string;
    }>(`/api/v1/folders/${id}`, data);
  }

  /**
   * Delete folder category
   * Removes Gmail label and deletes folder from database
   * @param id - Folder ID
   */
  async deleteFolder(id: number) {
    return this.delete<void>(`/api/v1/folders/${id}`);
  }

  // ============================================
  // Notification Preferences Methods
  // ============================================

  /**
   * Get user notification preferences
   * Returns batch settings, quiet hours, and priority notification configuration
   * Default values returned if preferences not yet configured
   */
  async getNotificationPrefs() {
    return this.get<{
      id: number;
      user_id: number;
      batch_enabled: boolean;
      batch_time: string;
      quiet_hours_enabled: boolean;
      quiet_hours_start: string;
      quiet_hours_end: string;
      priority_immediate: boolean;
      min_confidence_threshold: number;
      created_at: string;
      updated_at: string;
    }>('/api/v1/settings/notifications');
  }

  /**
   * Update user notification preferences
   * All fields optional for partial updates
   * Changes take effect immediately
   * @param data - Notification preferences update payload
   */
  async updateNotificationPrefs(data: {
    batch_enabled?: boolean;
    batch_time?: string;
    quiet_hours_enabled?: boolean;
    quiet_hours_start?: string;
    quiet_hours_end?: string;
    priority_immediate?: boolean;
    min_confidence_threshold?: number;
  }) {
    return this.put<{
      id: number;
      user_id: number;
      batch_enabled: boolean;
      batch_time: string;
      quiet_hours_enabled: boolean;
      quiet_hours_start: string;
      quiet_hours_end: string;
      priority_immediate: boolean;
      min_confidence_threshold: number;
      created_at: string;
      updated_at: string;
    }>('/api/v1/settings/notifications', data);
  }

  /**
   * Send test notification to user's Telegram
   * Requires active Telegram connection
   * Used to verify notification delivery and preferences
   */
  async testNotification() {
    return this.post<{
      message: string;
      success: boolean;
    }>('/api/v1/settings/notifications/test');
  }

  // ============================================
  // User Management Methods
  // ============================================

  /**
   * Update current user profile
   * Used to mark onboarding completion and update user preferences
   * @param data - User update payload (partial updates supported)
   */
  async updateUser(data: {
    onboarding_completed?: boolean;
  }) {
    return this.patch<{
      id: string;
      email: string;
      gmail_connected: boolean;
      telegram_connected: boolean;
      onboarding_completed: boolean;
      created_at: string;
      updated_at: string;
    }>('/api/v1/users/me', data);
  }

  // ============================================
  // Dashboard Methods
  // ============================================

  /**
   * Get dashboard statistics
   * Returns connection status, email processing stats, time saved metrics, and recent activity
   * Auto-refreshes every 30 seconds when used with SWR
   */
  async getDashboardStats() {
    return this.get<{
      connections: {
        gmail: {
          connected: boolean;
          last_sync?: string;
          error?: string;
        };
        telegram: {
          connected: boolean;
          last_sync?: string;
          error?: string;
        };
      };
      email_stats: {
        total_processed: number;
        pending_approval: number;
        auto_sorted: number;
        responses_sent: number;
      };
      time_saved: {
        today_minutes: number;
        total_minutes: number;
      };
      recent_activity: {
        id: number;
        type: 'sorted' | 'response_sent' | 'rejected';
        email_subject: string;
        timestamp: string;
        folder_name?: string;
      }[];
      rag_indexing_in_progress?: boolean;
      rag_indexing_progress?: number;
    }>('/api/v1/dashboard/stats');
  }

  /**
   * Get recent email activity feed
   * Returns last N email actions (sorted, sent, rejected)
   * @param limit - Number of recent activities to return (default: 10)
   */
  async getRecentActivity(limit: number = 10) {
    return this.get<{
      id: number;
      type: 'sorted' | 'response_sent' | 'rejected';
      email_subject: string;
      timestamp: string;
      folder_name?: string;
    }[]>(`/api/v1/dashboard/activity?limit=${limit}`);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
