/**
 * Notification Preferences Types
 * Types for user notification settings including batch, quiet hours, and priority alerts
 */

/**
 * Complete notification preferences object returned from backend
 */
export interface NotificationPreferences {
  id: number;
  user_id: number;
  batch_enabled: boolean;
  batch_time: string; // HH:MM format (24-hour)
  quiet_hours_enabled: boolean;
  quiet_hours_start: string; // HH:MM format (24-hour)
  quiet_hours_end: string; // HH:MM format (24-hour)
  priority_immediate: boolean;
  min_confidence_threshold: number; // 0.0 - 1.0 range
  created_at: string;
  updated_at: string;
}

/**
 * Request payload for updating notification preferences
 * All fields optional for partial updates
 */
export interface UpdateNotificationPrefsRequest {
  batch_enabled?: boolean;
  batch_time?: string; // HH:MM format
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string; // HH:MM format
  quiet_hours_end?: string; // HH:MM format
  priority_immediate?: boolean;
  min_confidence_threshold?: number; // 0.0 - 1.0
}

/**
 * Test notification response
 */
export interface TestNotificationResponse {
  message: string;
  success: boolean;
}

/**
 * Default notification preferences following best practices
 */
export const DEFAULT_NOTIFICATION_PREFERENCES: Omit<
  NotificationPreferences,
  'id' | 'user_id' | 'created_at' | 'updated_at'
> = {
  batch_enabled: true,
  batch_time: '18:00', // End of day
  quiet_hours_enabled: true,
  quiet_hours_start: '22:00', // Night time
  quiet_hours_end: '08:00', // Morning
  priority_immediate: true,
  min_confidence_threshold: 0.7, // 70% confidence
};
