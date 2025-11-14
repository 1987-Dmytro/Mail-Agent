import { useState } from 'react';
import type { FolderCategory } from '@/types/folder';

/**
 * Onboarding wizard state interface
 * Tracks progress and completion status across all steps
 */
export interface OnboardingProgress {
  currentStep: number;
  gmailConnected: boolean;
  telegramConnected: boolean;
  folders: FolderCategory[];
  gmailEmail?: string;
  telegramUsername?: string;
  lastUpdated: string;
}

/**
 * localStorage key for onboarding progress
 */
const STORAGE_KEY = 'onboarding_progress';

/**
 * Maximum age of stored progress before considering it stale (7 days)
 */
const MAX_PROGRESS_AGE_DAYS = 7;

/**
 * Result type for loading progress from localStorage
 * Includes both the progress data and stale status
 */
interface LoadProgressResult {
  progress: OnboardingProgress | null;
  isStale: boolean;
}

/**
 * Load and validate progress from localStorage
 * Handles data validation, corruption, and staleness detection
 *
 * @returns Object containing loaded progress and stale status
 */
function loadProgressFromStorage(): LoadProgressResult {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return { progress: null, isStale: false };
    }

    const progress: OnboardingProgress = JSON.parse(stored);

    // Validate required fields
    if (
      typeof progress.currentStep !== 'number' ||
      typeof progress.gmailConnected !== 'boolean' ||
      typeof progress.telegramConnected !== 'boolean'
    ) {
      console.warn('Invalid onboarding progress data. Clearing storage.');
      localStorage.removeItem(STORAGE_KEY);
      return { progress: null, isStale: false };
    }

    // Check if progress is stale
    let isStale = false;
    if (progress.lastUpdated) {
      const lastUpdated = new Date(progress.lastUpdated);
      const daysSinceUpdate = (Date.now() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);

      if (daysSinceUpdate > MAX_PROGRESS_AGE_DAYS) {
        console.warn(`Onboarding progress is stale (${daysSinceUpdate.toFixed(1)} days old)`);
        isStale = true;
      }
    }

    return { progress, isStale };
  } catch (error) {
    console.error('Failed to load onboarding progress from localStorage:', error);
    // Corrupted data - clear it
    localStorage.removeItem(STORAGE_KEY);
    return { progress: null, isStale: false };
  }
}

/**
 * Combined state interface for progress tracking
 * Avoids double-loading by keeping related state together
 */
interface ProgressState {
  savedProgress: OnboardingProgress | null;
  isProgressStale: boolean;
}

/**
 * useOnboardingProgress - Custom hook for wizard state persistence
 *
 * Responsibilities:
 * - Save wizard state to localStorage on every state change
 * - Load wizard state from localStorage on mount (using lazy initialization)
 * - Detect stale progress (>7 days old) and warn user
 * - Handle corrupted localStorage data gracefully
 * - Clear localStorage on completion
 *
 * Returns:
 * - savedProgress: Previously saved progress from localStorage (or null)
 * - isProgressStale: Whether saved progress is >7 days old
 * - saveProgress: Function to save current progress
 * - clearProgress: Function to clear localStorage progress
 *
 * Usage:
 * const { savedProgress, isProgressStale, clearProgress } = useOnboardingProgress();
 *
 * Implementation Notes:
 * - Uses lazy state initialization to avoid setState in useEffect
 * - Follows React 19 best practices for initial state loading
 * - Single state object prevents double-loading from localStorage
 * - No ESLint suppressions needed - clean React pattern
 */
export function useOnboardingProgress() {
  // Lazy initialization: Load from localStorage only once on mount
  // This avoids the need for setState in useEffect, following React best practices
  // Using a single state object with lazy initialization ensures we only load once
  const [state, setState] = useState<ProgressState>(() => {
    const { progress, isStale } = loadProgressFromStorage();
    return {
      savedProgress: progress,
      isProgressStale: isStale,
    };
  });

  /**
   * Save progress to localStorage
   * @param progress - Current onboarding progress to save
   */
  const saveProgress = (progress: OnboardingProgress): void => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    } catch (error) {
      console.error('Failed to save onboarding progress to localStorage:', error);
    }
  };

  /**
   * Clear progress from localStorage
   * Called when onboarding is completed
   */
  const clearProgress = (): void => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      setState({
        savedProgress: null,
        isProgressStale: false,
      });
    } catch (error) {
      console.error('Failed to clear onboarding progress from localStorage:', error);
    }
  };

  return {
    savedProgress: state.savedProgress,
    isProgressStale: state.isProgressStale,
    saveProgress,
    clearProgress,
  };
}
