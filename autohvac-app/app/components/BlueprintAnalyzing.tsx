import React, { useState, useEffect } from 'react';

interface BlueprintAnalyzingProps {
  processingStatus: string;
  fileName: string;
  onComplete?: () => void;
}

const analysisSteps = [
  { id: 1, label: 'Parsing blueprint structure', duration: 15000 },
  { id: 2, label: 'Identifying rooms and spaces', duration: 20000 },
  { id: 3, label: 'Calculating thermal loads', duration: 25000 },
  { id: 4, label: 'Analyzing ventilation requirements', duration: 20000 },
  { id: 5, label: 'Generating HVAC recommendations', duration: 15000 },
  { id: 6, label: 'Finalizing professional report', duration: 10000 }
];

export default function BlueprintAnalyzing({ processingStatus, fileName, onComplete }: BlueprintAnalyzingProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const totalDuration = analysisSteps.reduce((sum, step) => sum + step.duration, 0);
    let elapsedTime = 0;
    
    const progressInterval = setInterval(() => {
      elapsedTime += 500;
      const overallProgress = Math.min((elapsedTime / totalDuration) * 100, 95);
      setProgress(overallProgress);

      // Determine current step based on elapsed time
      let cumulativeTime = 0;
      for (let i = 0; i < analysisSteps.length; i++) {
        cumulativeTime += analysisSteps[i].duration;
        if (elapsedTime <= cumulativeTime) {
          setCurrentStep(i);
          setCompletedSteps(Array.from({ length: i }, (_, idx) => idx));
          break;
        }
      }
    }, 500);

    return () => clearInterval(progressInterval);
  }, []);

  // Handle completion from parent component
  useEffect(() => {
    if (processingStatus.includes('complete')) {
      setProgress(100);
      setCompletedSteps(analysisSteps.map((_, idx) => idx));
      setCurrentStep(analysisSteps.length - 1);
      setTimeout(() => onComplete?.(), 1500);
    }
  }, [processingStatus, onComplete]);

  return (
    <div className="w-full max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-lg">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-blue-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-hvac-navy mb-2">Analyzing Your Blueprint</h2>
        <p className="text-gray-600">Processing <span className="font-medium">{fileName}</span></p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Analysis Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Analysis Steps */}
      <div className="space-y-4 mb-8">
        {analysisSteps.map((step, index) => (
          <div key={step.id} className="flex items-center space-x-4">
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
              completedSteps.includes(index)
                ? 'bg-green-500 border-green-500 text-white'
                : currentStep === index
                ? 'bg-blue-500 border-blue-500 text-white animate-pulse'
                : 'bg-gray-100 border-gray-300 text-gray-400'
            }`}>
              {completedSteps.includes(index) ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <span className="text-sm font-medium">{step.id}</span>
              )}
            </div>
            <div className={`flex-1 transition-all duration-300 ${
              currentStep === index ? 'text-blue-600 font-medium' : 
              completedSteps.includes(index) ? 'text-green-600' : 'text-gray-500'
            }`}>
              {step.label}
              {currentStep === index && (
                <div className="flex space-x-1 mt-1">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Status Message */}
      <div className="text-center">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-800 font-medium">{processingStatus || 'Processing blueprint...'}</p>
          <p className="text-blue-600 text-sm mt-1">
            This typically takes 2-3 minutes for professional analysis
          </p>
        </div>
      </div>

      {/* Technical Details (Optional) */}
      <div className="mt-6 text-xs text-gray-500 text-center">
        <p>Our AI is performing advanced thermal load calculations and HVAC system optimization</p>
      </div>
    </div>
  );
}