/**
 * Dashboard Data Types
 * Defines interfaces for dashboard statistics, connection status, and activity items
 */

/**
 * Connection status for Gmail and Telegram integrations
 */
export interface ConnectionStatus {
  connected: boolean;
  last_sync?: string; // ISO timestamp
  error?: string;
}

/**
 * Activity item representing recent email actions
 */
export interface ActivityItem {
  id: number;
  type: 'sorted' | 'response_sent' | 'rejected';
  email_subject: string;
  timestamp: string; // ISO timestamp
  folder_name?: string; // Only for type='sorted'
}

/**
 * Complete dashboard statistics data structure
 */
export interface DashboardStats {
  connections: {
    gmail: ConnectionStatus;
    telegram: ConnectionStatus;
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
  recent_activity: ActivityItem[];
  rag_indexing_in_progress?: boolean; // Optional field for Epic 3
  rag_indexing_progress?: number; // Optional 0-100 percentage
}
