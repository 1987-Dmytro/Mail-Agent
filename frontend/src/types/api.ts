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
