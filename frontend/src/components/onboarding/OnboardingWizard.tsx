'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import type { FolderCategory } from '@/types/folder';
import WizardProgress from './WizardProgress';
import WelcomeStep from './WelcomeStep';
import GmailStep from './GmailStep';
import TelegramStep from './TelegramStep';
import FolderSetupStep from './FolderSetupStep';
import CompletionStep from './CompletionStep';

/**
 * Wizard step configuration interface
 * Defines structure for each step in the onboarding wizard
 */
export interface WizardStep {
  step: number;
  title: string;
  component: React.ComponentType<StepProps>;
  isComplete: boolean;
}

/**
 * Props passed to each step component
 * Provides callbacks for navigation and state updates
 */
export interface StepProps {
  onNext: () => void;
  onBack: () => void;
  onStepComplete: (data: Partial<OnboardingState>) => void;
  currentState: OnboardingState;
}

/**
 * Onboarding wizard state interface
 * Tracks progress and completion status across all steps
 */
export interface OnboardingState {
  currentStep: number;
  gmailConnected: boolean;
  telegramConnected: boolean;
  folders: FolderCategory[];
  gmailEmail?: string;
  telegramUsername?: string;
  lastUpdated: string;
}

/**
 * OnboardingWizard - Main orchestration component for multi-step onboarding
 *
 * Responsibilities:
 * - Manages wizard state (current step, completion tracking)
 * - Enforces step validation before allowing navigation
 * - Persists progress to localStorage
 * - Orchestrates 5 step components (Welcome, Gmail, Telegram, Folders, Complete)
 *
 * Architecture Pattern: Container/Presentation
 * - Container (this component): State management, business logic, validation
 * - Presentation (step components): UI rendering, user interaction
 */
export default function OnboardingWizard() {
  const router = useRouter();

  // ============================================
  // CRITICAL: Extract token from URL SYNCHRONOUSLY before any rendering
  // This must happen BEFORE any API calls to prevent 403 errors
  // ============================================
  if (typeof window !== 'undefined') {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
      // Store token IMMEDIATELY in localStorage
      localStorage.setItem('auth_token', token);
      console.log('OAuth token extracted from URL and stored synchronously');
    }
  }

  // ============================================
  // State Management
  // ============================================

  /**
   * Current wizard step (1-5)
   * Step 1: Welcome
   * Step 2: Gmail Connection
   * Step 3: Telegram Linking
   * Step 4: Folder Setup
   * Step 5: Completion
   */
  const [currentStep, setCurrentStep] = useState<number>(1);

  /**
   * Step completion tracking
   * Used to enforce validation before allowing Next navigation
   */
  const [gmailConnected, setGmailConnected] = useState<boolean>(false);
  const [telegramConnected, setTelegramConnected] = useState<boolean>(false);
  const [folders, setFolders] = useState<FolderCategory[]>([]);

  /**
   * Optional metadata for summary display
   */
  const [gmailEmail, setGmailEmail] = useState<string | undefined>(undefined);
  const [telegramUsername, setTelegramUsername] = useState<string | undefined>(undefined);

  /**
   * Track initial mount to prevent SAVE useEffect from running before LOAD useEffect
   * BUG FIX: SAVE useEffect was overwriting localStorage before LOAD useEffect could restore saved state
   * This caused OAuth navigation to reset wizard progress from step 2 → step 1
   */
  const isInitialMount = useRef(true);

  // ============================================
  // Step Configuration
  // ============================================

  /**
   * Step titles for progress indicator
   * Maps step number to display title
   */
  const stepTitles = [
    'Welcome',
    'Connect Gmail',
    'Link Telegram',
    'Setup Folders',
    'Complete',
  ];

  /**
   * Total number of steps in wizard
   */
  const totalSteps = 5;

  // ============================================
  // Validation Logic
  // ============================================

  /**
   * Step validation rules
   * Each step defines criteria that must be met before proceeding to next step
   *
   * Validation Rules:
   * - Step 1 (Welcome): No validation, always can proceed
   * - Step 2 (Gmail): gmailConnected === true required
   * - Step 3 (Telegram): telegramConnected === true required
   * - Step 4 (Folders): folders.length >= 1 required
   * - Step 5 (Complete): No validation, just navigate to dashboard
   */
  const canProceedToNextStep = (): boolean => {
    switch (currentStep) {
      case 1:
        return true; // Welcome step, always can proceed
      case 2:
        return gmailConnected;
      case 3:
        return telegramConnected;
      case 4:
        return folders.length >= 1;
      case 5:
        return true; // Completion step, no validation
      default:
        return false;
    }
  };

  /**
   * Validation error messages
   * Displayed when user tries to proceed without meeting step requirements
   */
  const getValidationErrorMessage = (): string | null => {
    if (canProceedToNextStep()) return null;

    switch (currentStep) {
      case 2:
        return 'Please connect your Gmail account before proceeding.';
      case 3:
        return 'Please link your Telegram account before proceeding.';
      case 4:
        return 'Please create at least 1 folder category before proceeding.';
      default:
        return null;
    }
  };

  // ============================================
  // Navigation Handlers
  // ============================================

  /**
   * Handle Next button click
   * Validates current step before advancing
   */
  const handleNext = () => {
    if (!canProceedToNextStep()) {
      // Show validation error (implementation can use toast or inline error)
      const errorMessage = getValidationErrorMessage();
      if (errorMessage) {
        console.warn('Validation failed:', errorMessage);
        // TODO: Display error via toast notification (Sonner)
      }
      return;
    }

    // Advance to next step
    if (currentStep < totalSteps) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  /**
   * Handle Back button click
   * Returns to previous step (disabled on step 1)
   */
  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  /**
   * Handle step completion callback
   * Called by step components to update wizard state
   * @param data - Partial state updates from step component
   */
  const handleStepComplete = (data: Partial<OnboardingState>) => {
    if (data.gmailConnected !== undefined) setGmailConnected(data.gmailConnected);
    if (data.telegramConnected !== undefined) setTelegramConnected(data.telegramConnected);
    if (data.folders !== undefined) setFolders(data.folders);
    if (data.gmailEmail !== undefined) setGmailEmail(data.gmailEmail);
    if (data.telegramUsername !== undefined) setTelegramUsername(data.telegramUsername);
  };

  /**
   * Handle skip step
   * Move to the next onboarding step without completing the current one
   * Provides escape path when users encounter errors
   */
  const handleSkip = () => {
    console.log(`[Onboarding] User skipped step ${currentStep}`);
    handleNext(); // Just move to next step
  };

  // ============================================
  // localStorage Persistence (AC9)
  // ============================================

  /**
   * Save wizard state to localStorage on every state change
   * Enables browser refresh resilience
   *
   * BUG FIX: Skip save on initial mount to allow LOAD useEffect to restore saved state first
   * Without this, SAVE would overwrite localStorage with initial state (currentStep: 1)
   * before LOAD could restore the saved progress (e.g., currentStep: 2)
   */
  useEffect(() => {
    // Skip save on initial mount - allow LOAD useEffect to run first
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    const state: OnboardingState = {
      currentStep,
      gmailConnected,
      telegramConnected,
      folders,
      gmailEmail,
      telegramUsername,
      lastUpdated: new Date().toISOString(),
    };

    try {
      localStorage.setItem('onboarding_progress', JSON.stringify(state));
    } catch (error) {
      console.error('Failed to save onboarding progress to localStorage:', error);
    }
  }, [currentStep, gmailConnected, telegramConnected, folders, gmailEmail, telegramUsername]);

  /**
   * Handle OAuth callback with token from URL
   * Backend redirects here after successful OAuth with token parameter
   */
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const email = urlParams.get('email');

    if (token) {
      // Store token in localStorage
      localStorage.setItem('auth_token', token);
      console.log('OAuth token received and stored');

      // Mark Gmail as connected
      // eslint-disable-next-line react-hooks/set-state-in-effect -- OAuth callback handling
      setGmailConnected(true);

      if (email) {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- OAuth callback handling
        setGmailEmail(email);
      }

      // CRITICAL FIX: Immediately save state to localStorage after OAuth
      const oauthState: OnboardingState = {
        currentStep: 2,
        gmailConnected: true,
        telegramConnected: false,
        folders: [],
        gmailEmail: email || undefined,
        telegramUsername: undefined,
        lastUpdated: new Date().toISOString(),
      };
      localStorage.setItem('onboarding_progress', JSON.stringify(oauthState));
      console.log('OAuth state saved to localStorage');

      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  /**
   * Load wizard state from localStorage on mount
   * Enables users to resume onboarding from where they left off
   *
   * CRITICAL: Also validates authentication token
   * If user is on Step 3+ but has no valid token, force back to Step 2 (Gmail)
   */
  useEffect(() => {
    const loadAndValidateProgress = async () => {
      try {
        const savedProgress = localStorage.getItem('onboarding_progress');
        if (savedProgress) {
          const state: OnboardingState = JSON.parse(savedProgress);

          // Check if progress is stale (>7 days old)
          const lastUpdated = new Date(state.lastUpdated);
          const daysSinceUpdate = (Date.now() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);

          if (daysSinceUpdate > 7) {
            console.warn('Onboarding progress is stale (>7 days old). Starting fresh.');
            localStorage.removeItem('onboarding_progress');
            localStorage.removeItem('auth_token');
            return;
          }

          // CRITICAL: Validate token before restoring state
          const token = localStorage.getItem('auth_token');

          // If on Step 3+ but no token exists, force back to Step 2 (Gmail)
          if (state.currentStep >= 3 && !token) {
            console.warn('No auth token found - forcing back to Gmail connection (Step 2)');
            // eslint-disable-next-line react-hooks/set-state-in-effect -- Security validation requires state reset
            setCurrentStep(2);
            setGmailConnected(false);
            setTelegramConnected(false);
            localStorage.removeItem('onboarding_progress');
            return;
          }

          // CRITICAL: Validate token is actually valid by calling auth status API
          if (state.currentStep >= 3 && token) {
            try {
              const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/status`, {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              });
              const data = await response.json();

              // If token is invalid (user doesn't exist), clear localStorage and restart
              if (!data.authenticated) {
                console.warn('Auth token is invalid - user does not exist. Clearing localStorage and restarting onboarding.');
                localStorage.removeItem('onboarding_progress');
                localStorage.removeItem('auth_token');
                setCurrentStep(1);
                setGmailConnected(false);
                setTelegramConnected(false);
                setFolders([]);
                return;
              }
            } catch (error) {
              console.error('Failed to validate auth token:', error);
              // Network error - proceed with caution, don't block user
            }
          }

          // Restore state (initial load from localStorage is acceptable)
          // eslint-disable-next-line react-hooks/set-state-in-effect -- Loading initial wizard state from localStorage on mount is a valid use case
          setCurrentStep(state.currentStep);
          setGmailConnected(state.gmailConnected);
          setTelegramConnected(state.telegramConnected);
          setFolders(state.folders || []);
          setGmailEmail(state.gmailEmail);
          setTelegramUsername(state.telegramUsername);
        }
      } catch (error) {
        console.error('Failed to load onboarding progress from localStorage:', error);
        // Corrupted localStorage data - reset to step 1
        localStorage.removeItem('onboarding_progress');
        localStorage.removeItem('auth_token');
      }
    };

    loadAndValidateProgress();
  }, []); // Only run on mount

  // ============================================
  // Render
  // ============================================

  /**
   * Current wizard state for passing to step components
   */
  const wizardState: OnboardingState = {
    currentStep,
    gmailConnected,
    telegramConnected,
    folders,
    gmailEmail,
    telegramUsername,
    lastUpdated: new Date().toISOString(),
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8"
      style={{
        // Safari-specific fixes for flexbox centering
        WebkitBoxAlign: 'center',
        WebkitBoxPack: 'center',
        minHeight: '100vh',
      }}
    >
      <div className="w-full max-w-2xl mx-auto space-y-8">
        {/* Progress indicator (AC1) */}
        <WizardProgress
          currentStep={currentStep}
          totalSteps={totalSteps}
          stepTitles={stepTitles}
        />

        {/* Wizard card - centered content */}
        <div className="bg-card rounded-lg shadow-lg p-8 w-full">
          <div className="mx-auto max-w-lg">
            {/* Step component renderer */}
            <div className="mb-8">
              {currentStep === 1 && (
                <WelcomeStep
                  onNext={handleNext}
                  onBack={handleBack}
                  onStepComplete={handleStepComplete}
                  currentState={wizardState}
                />
              )}
              {currentStep === 2 && (
                <GmailStep
                  onNext={handleNext}
                  onBack={handleBack}
                  onStepComplete={handleStepComplete}
                  currentState={wizardState}
                />
              )}
              {currentStep === 3 && (
                <TelegramStep
                  onNext={handleNext}
                  onBack={handleBack}
                  onStepComplete={handleStepComplete}
                  currentState={wizardState}
                />
              )}
              {currentStep === 4 && (
                <FolderSetupStep
                  onNext={handleNext}
                  onBack={handleBack}
                  onStepComplete={handleStepComplete}
                  currentState={wizardState}
                />
              )}
              {currentStep === 5 && (
                <CompletionStep
                  onNext={handleNext}
                  onBack={handleBack}
                  onStepComplete={handleStepComplete}
                  currentState={wizardState}
                />
              )}
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center justify-between">
              <button
                onClick={handleBack}
                disabled={currentStep === 1}
                className="rounded-md border px-4 py-2 disabled:opacity-50"
              >
                Back
              </button>

              <button
                onClick={handleNext}
                disabled={!canProceedToNextStep()}
                className="rounded-md bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
              >
                {currentStep === totalSteps ? 'Complete' : 'Next'}
              </button>
            </div>

            {/* Validation error message */}
            {!canProceedToNextStep() && (
              <div
                className="mt-6 mb-6 w-full p-4 rounded-lg bg-red-50 border border-red-200"
                style={{
                  zIndex: 10,
                  marginTop: '1.5rem',
                  marginBottom: '1.5rem',
                }}
              >
                <div className="flex items-start space-x-3">
                  <svg
                    className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <p className="text-sm text-red-800 text-left leading-relaxed">
                    {getValidationErrorMessage()}
                  </p>
                </div>
              </div>
            )}

            {/* Skip setup link - available on all steps except completion */}
            {currentStep < totalSteps && (
              <div className="mt-4 text-center">
                <button
                  onClick={handleSkip}
                  className="text-sm text-muted-foreground hover:text-foreground underline transition-colors"
                >
                  Skip setup—I&apos;ll configure this later
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
