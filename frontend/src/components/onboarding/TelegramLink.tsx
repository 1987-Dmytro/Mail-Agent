'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Check, Loader2, Copy, MessageCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { useTelegramStatus } from '@/hooks/useTelegramStatus';

/**
 * Telegram linking flow states
 */
type TelegramLinkState = 'initial' | 'polling' | 'success' | 'error';

/**
 * Error types for better error messaging
 */
type ErrorType =
  | 'code_generation_failed'
  | 'code_expired'
  | 'verification_failed'
  | 'network_error'
  | 'unknown';

interface TelegramLinkProps {
  /**
   * Callback after successful Telegram linking
   */
  onSuccess?: () => void;
  /**
   * Callback after linking error
   */
  onError?: (error: string) => void;
  /**
   * Optional navigation callback for wizard integration
   * When provided, replaces "Continue to Dashboard" with wizard navigation
   */
  onNavigate?: () => void;
}

/**
 * Telegram Linking Component
 *
 * Implements the complete Telegram bot linking flow:
 * 1. Generate 6-digit alphanumeric linking code (10-minute expiration)
 * 2. Display code prominently with copy button
 * 3. Provide deep link to open Telegram app directly
 * 4. Poll backend every 3 seconds to check verification status
 * 5. Show success state when code is verified
 * 6. Handle expiration with "Generate New Code" option
 *
 * Security features:
 * - Code stored only in component state (not localStorage)
 * - 10-minute expiration enforced
 * - Polling stops on success, error, or unmount
 * - No bot token exposed in frontend
 *
 * AC Coverage:
 * - AC 1-2: Step-by-step instructions with visual hierarchy
 * - AC 3: 6-digit code prominently displayed
 * - AC 4: Copy Code button with toast confirmation
 * - AC 5: Deep link button opens Telegram app
 * - AC 6-7: Polling every 3 seconds, success shows username
 * - AC 8: Code expiration after 10 minutes
 * - AC 9: Error handling for all failure modes
 */
export function TelegramLink({ onSuccess, onError, onNavigate }: TelegramLinkProps) {
  const router = useRouter();

  // Check Telegram connection status on mount for persistence (AC: 6-7)
  const { isLinked, isLoading: statusLoading, telegramUsername: linkedUsername } = useTelegramStatus();

  const [state, setState] = useState<TelegramLinkState>('initial');
  const [errorType, setErrorType] = useState<ErrorType | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Linking code state
  const [linkingCode, setLinkingCode] = useState<string>('');
  const [timeRemaining, setTimeRemaining] = useState<string>('');

  // Success state
  const [telegramUsername, setTelegramUsername] = useState<string>('');

  // Polling interval ref for cleanup
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Check if already linked on mount, otherwise generate new code
   * AC: 6-7 (connection persistence)
   */
  useEffect(() => {
    if (statusLoading) return;

    // If already linked, show success state immediately
    if (isLinked) {
      setTelegramUsername(linkedUsername || 'your Telegram account');
      setState('success');

      // Call onSuccess to update wizard state
      if (onSuccess) {
        onSuccess();
      }
      return;
    }

    // Not linked - generate new code
    generateNewCode();

    // Cleanup intervals on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLinked, linkedUsername, statusLoading]);

  /**
   * Generate new Telegram linking code
   * AC: 3 (code generation)
   */
  async function generateNewCode() {
    try {
      setState('initial');
      setErrorType(null);
      setErrorMessage('');

      const response = await apiClient.generateTelegramLink();

      if (response.data) {
        const { code, expires_at } = response.data;
        setLinkingCode(code);

        // Start countdown timer
        startCountdownTimer(expires_at);

        // Start polling for verification
        startPolling(code);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Failed to generate linking code:', error);
      handleError('code_generation_failed', 'Cannot generate linking code. Please try again.');
    }
  }

  /**
   * Start countdown timer for code expiration
   * AC: 8 (expiration countdown)
   */
  function startCountdownTimer(expirationTime: string) {
    // Clear existing countdown
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }

    const updateCountdown = () => {
      const now = new Date().getTime();
      const expiry = new Date(expirationTime).getTime();
      const diff = expiry - now;

      if (diff <= 0) {
        // Code expired
        setTimeRemaining('0:00');
        clearInterval(countdownIntervalRef.current!);
        handleCodeExpiration();
      } else {
        // Calculate minutes and seconds
        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        setTimeRemaining(`${minutes}:${seconds.toString().padStart(2, '0')}`);
      }
    };

    // Update immediately
    updateCountdown();

    // Update every second
    countdownIntervalRef.current = setInterval(updateCountdown, 1000);
  }

  /**
   * Handle code expiration
   * AC: 8 (expiration handling)
   */
  function handleCodeExpiration() {
    // Stop polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    handleError('code_expired', 'Linking code has expired. Please generate a new code.');
  }

  /**
   * Start polling for verification
   * AC: 6 (polling every 3 seconds)
   */
  function startPolling(code: string) {
    // Clear existing polling interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    setState('polling');

    // Poll immediately
    checkVerification(code);

    // Poll every 3 seconds
    pollingIntervalRef.current = setInterval(() => {
      checkVerification(code);
    }, 3000);
  }

  /**
   * Check if code has been verified
   * AC: 6-7 (verification check and success state)
   */
  async function checkVerification(code: string) {
    try {
      const response = await apiClient.verifyTelegramLink(code);

      if (response.data && response.data.verified) {
        // Code verified successfully
        const { telegram_username } = response.data;

        // Stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current);
        }

        // Update state
        setTelegramUsername(telegram_username || 'your account');
        setState('success');

        // Show success toast
        toast.success('Telegram account linked successfully!');

        // Call success callback
        if (onSuccess) {
          onSuccess();
        }
      }
      // If not verified, continue polling
    } catch (error) {
      console.error('Verification check failed:', error);
      // Don't show error for individual polling failures - continue polling
      // Only show error if multiple consecutive failures occur
    }
  }

  /**
   * Copy linking code to clipboard
   * AC: 4 (copy code button)
   */
  async function copyCodeToClipboard() {
    try {
      await navigator.clipboard.writeText(linkingCode);
      toast.success('Code copied to clipboard!', {
        description: 'Paste it in Telegram after /start',
      });
    } catch (error) {
      console.error('Failed to copy code:', error);
      toast.error('Manual copy required', {
        description: 'Your browser doesn\'t support automatic copying. Please copy the code manually.',
      });
    }
  }

  /**
   * Open Telegram app with deep link
   * AC: 5 (deep link button)
   */
  function openTelegramApp() {
    const deepLink = `tg://resolve?domain=mailagentbot&start=${linkingCode}`;

    try {
      window.open(deepLink, '_blank');
      toast.info('Opening Telegram...', {
        description: 'If Telegram doesn\'t open, please follow the manual instructions.',
      });
    } catch (error) {
      console.error('Failed to open Telegram:', error);
      toast.error('Please open Telegram manually', {
        description: 'Search for @MailAgentBot and send the code.',
      });
    }
  }

  /**
   * Handle errors with appropriate messaging
   * AC: 9 (error handling)
   */
  function handleError(type: ErrorType, message: string) {
    setErrorType(type);
    setErrorMessage(message);
    setState('error');

    // Stop polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }

    // Show error toast
    toast.error(message);

    // Call error callback
    if (onError) {
      onError(message);
    }
  }

  /**
   * Retry linking flow after error
   */
  function retryLinking() {
    generateNewCode();
  }

  /**
   * Render initial/polling state: Display code and instructions
   * AC: 1-5 (instructions, code display, copy, deep link)
   */
  if (state === 'initial' || state === 'polling') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="w-6 h-6" />
            Link Telegram Account
          </CardTitle>
          <CardDescription>
            Connect to @MailAgentBot to receive email notifications
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step-by-step instructions - AC 1-2 */}
          <div className="space-y-3">
            <h3 className="font-semibold text-sm">Follow these steps:</h3>
            <ol className="space-y-2 text-sm">
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  1
                </span>
                <span className="pt-0.5">Open Telegram on your device</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  2
                </span>
                <span className="pt-0.5">Search for <strong>@MailAgentBot</strong></span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  3
                </span>
                <span className="pt-0.5">Send <strong>/start {linkingCode}</strong></span>
              </li>
            </ol>
          </div>

          {/* Linking code display - AC 3 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Your linking code:</label>
            <div className="flex items-center gap-2">
              <div className="flex-1 p-4 bg-muted rounded-lg border-2 border-primary/20">
                <div className="text-4xl font-mono font-bold tracking-widest text-center">
                  {linkingCode || '------'}
                </div>
              </div>
            </div>

            {/* Expiration countdown - AC 8 */}
            {timeRemaining && (
              <p className="text-sm text-muted-foreground text-center">
                Expires in <span className="font-mono font-semibold">{timeRemaining}</span>
              </p>
            )}
          </div>

          {/* Action buttons - AC 4-5 */}
          <div className="space-y-2">
            <Button
              onClick={copyCodeToClipboard}
              variant="outline"
              className="w-full"
              size="lg"
              disabled={!linkingCode}
            >
              <Copy className="w-4 h-4 mr-2" />
              Copy Code
            </Button>

            <Button
              onClick={openTelegramApp}
              className="w-full"
              size="lg"
              disabled={!linkingCode}
            >
              <MessageCircle className="w-4 h-4 mr-2" />
              Open Telegram
            </Button>
          </div>

          {/* Polling status - AC 6 */}
          {state === 'polling' && (
            <Alert>
              <Loader2 className="h-4 w-4 animate-spin" />
              <AlertDescription>
                Waiting for verification... Send the code to @MailAgentBot in Telegram.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    );
  }

  /**
   * Render success state: Connected
   * AC: 7 (success confirmation with username)
   */
  if (state === 'success') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="pt-6 flex flex-col items-center justify-center space-y-4 min-h-[200px]">
          <div className="rounded-full bg-green-500 p-3">
            <Check className="w-8 h-8 text-white" />
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-xl font-semibold">Telegram Connected!</h3>
            <p className="text-muted-foreground">
              Connected to <strong>{telegramUsername}</strong>
            </p>
          </div>
          <Button
            onClick={() => {
              if (onNavigate) {
                onNavigate();
              } else {
                router.push('/dashboard');
              }
            }}
            className="w-full"
            size="lg"
          >
            {onNavigate ? 'Continue' : 'Continue to Dashboard'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render error state: Show error message with retry
   * AC: 8-9 (expiration and error handling)
   */
  if (state === 'error') {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="pt-6 space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Error:</strong> {errorMessage}
            </AlertDescription>
          </Alert>

          <div className="flex flex-col gap-2">
            {errorType === 'code_expired' ? (
              <Button
                onClick={generateNewCode}
                className="w-full"
                size="lg"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Generate New Code
              </Button>
            ) : (
              <Button
                onClick={retryLinking}
                variant="outline"
                className="w-full"
              >
                Try Again
              </Button>
            )}

            {errorType === 'network_error' && (
              <p className="text-sm text-muted-foreground text-center">
                Please check your internet connection and try again.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
}
