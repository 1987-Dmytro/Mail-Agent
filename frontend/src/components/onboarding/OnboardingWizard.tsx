'use client';

import { useState, useEffect, useRef } from 'react';
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
  // Future: Can add router navigation if needed
  // const router = useRouter(); // eslint-disable-line @typescript-eslint/no-unused-vars

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
   * Load wizard state from localStorage on mount
   * Enables users to resume onboarding from where they left off
   */
  useEffect(() => {
    try {
      const savedProgress = localStorage.getItem('onboarding_progress');
      if (savedProgress) {
        const state: OnboardingState = JSON.parse(savedProgress);

        // Check if progress is stale (>7 days old)
        const lastUpdated = new Date(state.lastUpdated);
        const daysSinceUpdate = (Date.now() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);

        if (daysSinceUpdate > 7) {
          console.warn('Onboarding progress is stale (>7 days old). Starting fresh.');
          // TODO: Show warning toast to user
          return;
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
    }
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
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="mx-auto max-w-3xl">
        {/* Progress indicator (AC1) */}
        <WizardProgress
          currentStep={currentStep}
          totalSteps={totalSteps}
          stepTitles={stepTitles}
        />

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
          <div className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {getValidationErrorMessage()}
          </div>
        )}
      </div>
    </div>
  );
}
