/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

/**
 * Paginated API response
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/**
 * API error response
 */
export interface ApiError {
  message: string;
  details?: unknown;
  status: number;
  code?: string;
}

/**
 * OAuth configuration response
 * Used for Gmail OAuth flow
 */
export interface OAuthConfig {
  auth_url: string;
  client_id: string;
  scopes: string[];
}
