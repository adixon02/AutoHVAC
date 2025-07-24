import React from 'react';
import { cn } from '@/lib/utils';

export interface Step {
  id: string;
  name: string;
  description?: string;
  status: 'complete' | 'current' | 'upcoming';
}

export interface ProgressIndicatorProps {
  steps: Step[];
  className?: string;
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ steps, className }) => {
  return (
    <div className={cn('premium-card p-6 mb-8', className)}>
      <nav aria-label="Progress">
        <ol className="flex items-center justify-center">
          {steps.map((step, stepIdx) => (
            <li
              key={step.id}
              className={cn(
                stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-16 md:pr-24' : '',
                'relative flex flex-col items-center'
              )}
            >
              {/* Connecting line */}
              {stepIdx !== steps.length - 1 && (
                <div className="absolute top-5 left-full w-8 sm:w-16 md:w-24 h-0.5 -translate-x-1/2">
                  <div
                    className={cn(
                      'h-full transition-all duration-500',
                      step.status === 'complete' 
                        ? 'premium-gradient' 
                        : 'bg-gray-200'
                    )}
                  />
                </div>
              )}
              
              {/* Step circle */}
              <div className="relative">
                {step.status === 'complete' ? (
                  <div className="relative flex h-10 w-10 items-center justify-center rounded-full premium-gradient shadow-lg animate-slide-up">
                    <svg
                      className="h-5 w-5 text-white"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <div className="absolute -inset-1 premium-gradient rounded-full blur opacity-25"></div>
                  </div>
                ) : step.status === 'current' ? (
                  <div
                    className="relative flex h-10 w-10 items-center justify-center rounded-full border-2 border-blue-500 bg-white shadow-lg animate-pulse"
                    aria-current="step"
                  >
                    <span className="h-3 w-3 rounded-full premium-gradient animate-pulse" aria-hidden="true" />
                    <div className="absolute -inset-1 border-2 border-blue-200 rounded-full animate-ping"></div>
                  </div>
                ) : (
                  <div className="group relative flex h-10 w-10 items-center justify-center rounded-full border-2 border-gray-300 bg-white hover:border-gray-400 transition-colors">
                    <span
                      className="h-3 w-3 rounded-full bg-gray-300 group-hover:bg-gray-400 transition-colors"
                      aria-hidden="true"
                    />
                  </div>
                )}
              </div>
              
              {/* Step label */}
              <div className="mt-3 text-center min-w-0">
                <span 
                  className={cn(
                    'text-sm font-semibold transition-colors',
                    step.status === 'complete' && 'text-blue-600',
                    step.status === 'current' && 'text-blue-600',
                    step.status === 'upcoming' && 'text-gray-500'
                  )}
                >
                  {step.name}
                </span>
                {step.description && (
                  <p className="text-xs professional-text mt-1">{step.description}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );
};

export { ProgressIndicator };