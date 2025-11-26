import { Check } from 'lucide-react';

/**
 * WizardProgress component props
 */
export interface WizardProgressProps {
  currentStep: number;
  totalSteps: number;
  stepTitles: string[];
}

/**
 * WizardProgress - Visual progress indicator for onboarding wizard
 *
 * Displays:
 * - Step numbers with visual indicators (1/5, 2/5, etc.)
 * - Step titles ("Welcome", "Connect Gmail", etc.)
 * - Current step highlighted (colored circle or bold text)
 * - Completed steps with checkmark icons ✓
 * - Future steps with muted styling
 * - Responsive design (horizontal on desktop, vertical/compact on mobile)
 *
 * Props:
 * - currentStep: Currently active step (1-based index)
 * - totalSteps: Total number of steps in wizard
 * - stepTitles: Array of step titles for display
 */
export default function WizardProgress({
  currentStep,
  totalSteps,
  stepTitles,
}: WizardProgressProps) {
  /**
   * Determine step status for visual styling
   * @param stepNumber - Step number to check (1-based)
   * @returns 'completed' | 'current' | 'future'
   */
  const getStepStatus = (stepNumber: number): 'completed' | 'current' | 'future' => {
    if (stepNumber < currentStep) return 'completed';
    if (stepNumber === currentStep) return 'current';
    return 'future';
  };

  return (
    <div className="mb-8">
      {/* Step progress summary (mobile-friendly) */}
      <div className="mb-4 text-center">
        <p className="text-sm text-muted-foreground">
          Step {currentStep} of {totalSteps}
        </p>
        <h2 className="text-xl font-semibold text-foreground">
          {stepTitles[currentStep - 1]}
        </h2>
      </div>

      {/* Visual step indicators (desktop: horizontal, mobile: compact) */}
      <div className="relative">
        {/* Progress bar container - centered with margins to align with circle centers */}
        <div
          className="absolute top-5 h-0.5 md:top-1/2"
          style={{
            left: '20px',
            right: '20px',
          }}
        >
          {/* Progress bar background */}
          <div className="absolute inset-0 bg-muted" />

          {/* Progress bar fill (completed portion) */}
          <div
            className="absolute left-0 top-0 h-full bg-primary transition-all duration-300"
            style={{
              width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%`,
            }}
          />
        </div>

        {/* Step circles */}
        <div className="relative flex justify-between">
          {Array.from({ length: totalSteps }, (_, index) => {
            const stepNumber = index + 1;
            const status = getStepStatus(stepNumber);

            return (
              <div key={stepNumber} className="flex flex-col items-center">
                {/* Step circle indicator */}
                <div
                  className={`
                    relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all
                    ${
                      status === 'completed'
                        ? 'border-primary bg-primary text-primary-foreground'
                        : status === 'current'
                          ? 'border-primary bg-background text-primary'
                          : 'border-muted bg-background text-muted-foreground'
                    }
                  `}
                >
                  {status === 'completed' ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <span className="text-sm font-semibold">{stepNumber}</span>
                  )}
                </div>

                {/* Step title (hidden on mobile, shown on desktop) */}
                <div className="mt-2 hidden text-center md:block">
                  <p
                    className={`
                      text-xs
                      ${
                        status === 'current'
                          ? 'font-semibold text-foreground'
                          : status === 'completed'
                            ? 'text-muted-foreground'
                            : 'text-muted-foreground/60'
                      }
                    `}
                  >
                    {stepTitles[index]}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
