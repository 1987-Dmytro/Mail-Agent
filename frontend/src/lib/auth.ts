/**
 * Authentication helper utilities
 * Manages JWT token storage and authentication state
 */

const TOKEN_KEY = 'mail_agent_token';

/**
 * Retrieve JWT token from storage
 * Tries localStorage first, falls back to sessionStorage
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    // Check localStorage first
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      return token;
    }

    // Fallback to sessionStorage
    return sessionStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error getting token:', error);
    return null;
  }
}

/**
 * Store JWT token in storage
 * Uses localStorage for persistence across sessions
 */
export function setToken(token: string, remember = true): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    if (remember) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      sessionStorage.setItem(TOKEN_KEY, token);
    }
  } catch (error) {
    console.error('Error setting token:', error);
  }
}

/**
 * Remove JWT token from storage
 * Clears from both localStorage and sessionStorage
 */
export function removeToken(): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error removing token:', error);
  }
}

/**
 * Check if user has a valid token
 * Note: This only checks if token exists, not if it's expired
 * Server-side validation will confirm actual validity
 */
export function isAuthenticated(): boolean {
  const token = getToken();
  return !!token;
}

/**
 * Decode JWT token payload (without verification)
 * WARNING: Do not trust this data for security decisions
 * Server must always verify token validity
 */
export function decodeToken(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) {
      return null;
    }

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );

    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Error decoding token:', error);
    return null;
  }
}

/**
 * Check if JWT token is expired
 * Returns true if token is expired or invalid
 */
export function isTokenExpired(token?: string | null): boolean {
  const tokenToCheck = token || getToken();

  if (!tokenToCheck) {
    return true;
  }

  try {
    const decoded = decodeToken(tokenToCheck);
    if (!decoded || !decoded.exp) {
      return true;
    }

    // exp is in seconds, Date.now() is in milliseconds
    const expirationTime = (decoded.exp as number) * 1000;
    return Date.now() >= expirationTime;
  } catch {
    // Invalid token format - treat as expired
    return true;
  }
}

/**
 * Get user info from token
 * Returns decoded user data if token is valid
 */
export function getUserFromToken(): Record<string, unknown> | null {
  const token = getToken();

  if (!token || isTokenExpired(token)) {
    return null;
  }

  return decodeToken(token);
}
