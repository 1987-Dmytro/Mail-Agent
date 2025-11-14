/**
 * OAuth and authentication-related type definitions
 */

/**
 * Gmail OAuth configuration returned from backend
 */
export interface GmailOAuthConfig {
  /** Google OAuth authorization URL with client_id and redirect_uri */
  auth_url: string;
  /** OAuth client ID (public value, safe to expose in frontend) */
  client_id: string;
  /** Requested Gmail API scopes */
  scopes: string[];
}

/**
 * OAuth callback parameters from Google redirect
 */
export interface OAuthCallbackParams {
  /** Authorization code from Google OAuth */
  code: string;
  /** CSRF state token for validation */
  state: string;
  /** Space-separated granted scopes */
  scope: string;
}

/**
 * OAuth callback request payload
 */
export interface OAuthCallbackRequest {
  /** Authorization code from Google */
  code: string;
  /** CSRF state token for validation */
  state: string;
}

/**
 * OAuth callback response from backend
 */
export interface OAuthCallbackResponse {
  /** Authenticated user object */
  user: {
    id: number;
    email: string;
    gmail_connected: boolean;
    telegram_connected: boolean;
  };
  /** JWT access token */
  token: string;
}

/**
 * Authentication status response
 */
export interface AuthStatusResponse {
  /** Whether user is authenticated */
  authenticated: boolean;
  /** User object if authenticated */
  user?: {
    id: number;
    email: string;
    gmail_connected: boolean;
    telegram_connected: boolean;
  };
}

/**
 * Telegram linking code response
 * Returned when generating a new linking code
 */
export interface TelegramLinkingCode {
  /** 6-digit alphanumeric linking code */
  code: string;
  /** ISO 8601 timestamp when code expires (10 minutes from generation) */
  expires_at: string;
  /** Whether code has been verified (always false initially) */
  verified: boolean;
}

/**
 * Telegram verification status response
 * Returned when checking if code has been verified
 */
export interface TelegramVerificationStatus {
  /** Whether the code has been successfully verified */
  verified: boolean;
  /** Telegram user ID if verified */
  telegram_id?: string;
  /** Telegram username (e.g., "@username") if verified */
  telegram_username?: string;
}

/**
 * Telegram connection status response
 * Returned when checking if user has already linked Telegram
 */
export interface TelegramConnectionStatus {
  /** Whether Telegram is currently connected */
  connected: boolean;
  /** Telegram user ID if connected */
  telegram_id?: string;
  /** Telegram username (e.g., "@username") if connected */
  telegram_username?: string;
}
