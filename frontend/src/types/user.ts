/**
 * User model
 */
export interface User {
  id: string;
  email: string;
  gmail_connected: boolean;
  telegram_connected: boolean;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Authentication state
 */
export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
}
