'use client';

interface ProgressStep {
  id: string;
  label: string;
}

interface ProgressIndicatorProps {
  steps: ProgressStep[];
  currentStep: string;
  className?: string;
}

export default function ProgressIndicator({ 
  steps, 
  currentStep, 
  className = '' 
}: ProgressIndicatorProps) {
  const currentIndex = steps.findIndex(step => step.id === currentStep);

  return (
    <div className={`mb-8 ${className}`}>
      {/* Progress Circles and Lines */}
      <div className="flex items-center justify-center">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div
              className={`
                w-12 h-12 rounded-full flex items-center justify-center font-semibold transition-all duration-300 ease-out shadow-soft
                ${currentStep === step.id 
                  ? 'bg-primary-600 text-white shadow-medium ring-4 ring-primary-100 scale-110' 
                  : currentIndex > index 
                    ? 'bg-success-500 text-white shadow-medium' 
                    : 'bg-neutral-200 text-neutral-500 hover:bg-neutral-300'
                }
              `}
            >
              {currentIndex > index ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              ) : (
                index + 1
              )}
            </div>
            
            {index < steps.length - 1 && (
              <div className={`w-24 h-2 mx-4 rounded-full transition-all duration-500 ease-out ${
                currentIndex > index ? 'bg-success-400' : 'bg-neutral-200'
              }`} />
            )}
          </div>
        ))}
      </div>
      
      {/* Step Labels */}
      <div className="flex justify-around mt-4">
        {steps.map((step) => (
          <span 
            key={step.id}
            className={`text-sm font-medium transition-all duration-300 ${
              currentStep === step.id 
                ? 'font-semibold text-primary-600 scale-105' 
                : 'text-neutral-600'
            }`}
          >
            {step.label}
          </span>
        ))}
      </div>
    </div>
  );
}