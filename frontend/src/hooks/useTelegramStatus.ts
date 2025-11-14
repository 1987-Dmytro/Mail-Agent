import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

/**
 * Telegram connection status hook
 *
 * Checks if user has already linked their Telegram account
 * Used for connection persistence across page refreshes
 *
 * Pattern follows useAuthStatus() from Story 4.2
 *
 * @returns {object} Connection status and helper methods
 * - isLinked: Whether Telegram is connected
 * - isLoading: Whether status check is in progress
 * - error: Error message if status check failed
 * - telegramUsername: Telegram username if connected
 * - telegramId: Telegram user ID if connected
 * - refresh: Function to manually refresh status
 */
export function useTelegramStatus() {
  const [isLinked, setIsLinked] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [telegramUsername, setTelegramUsername] = useState<string | null>(null);
  const [telegramId, setTelegramId] = useState<string | null>(null);

  /**
   * Check Telegram connection status
   */
  async function checkStatus() {
    try {
      setIsLoading(true);
      setError(null);

      const response = await apiClient.telegramStatus();

      if (response.data) {
        const { connected, telegram_username, telegram_id } = response.data;
        setIsLinked(connected);
        setTelegramUsername(telegram_username || null);
        setTelegramId(telegram_id || null);
      } else {
        setIsLinked(false);
        setTelegramUsername(null);
        setTelegramId(null);
      }
    } catch (err) {
      console.error('Failed to check Telegram status:', err);
      setError('Failed to check connection status');
      setIsLinked(false);
      setTelegramUsername(null);
      setTelegramId(null);
    } finally {
      setIsLoading(false);
    }
  }

  /**
   * Check status on mount
   */
  useEffect(() => {
    checkStatus();
  }, []);

  /**
   * Manual refresh function
   */
  const refresh = async () => {
    await checkStatus();
  };

  return {
    isLinked,
    isLoading,
    error,
    telegramUsername,
    telegramId,
    refresh,
  };
}
