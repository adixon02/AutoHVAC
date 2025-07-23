'use client';

import { ReactNode } from 'react';
import { Card, Button } from './';

interface ErrorStateProps {
  title?: string;
  message?: string;
  children?: ReactNode;
  onRetry?: () => void;
  onReset?: () => void;
  showRetry?: boolean;
  showReset?: boolean;
  icon?: 'error' | 'warning' | 'network';
}

const icons = {
  error: (
    <svg className="w-16 h-16 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  warning: (
    <svg className="w-16 h-16 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
    </svg>
  ),
  network: (
    <svg className="w-16 h-16 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
    </svg>
  )
};

export default function ErrorState({
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  children,
  onRetry,
  onReset,
  showRetry = true,
  showReset = false,
  icon = 'error'
}: ErrorStateProps) {
  return (
    <Card className="max-w-2xl mx-auto text-center">
      <div className="mb-6">
        <div className="mb-4 flex justify-center">
          {icons[icon]}
        </div>
        
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {title}
        </h2>
        
        <p className="text-gray-600">
          {message}
        </p>
      </div>
      
      {children && (
        <div className="mb-6 text-left">
          {children}
        </div>
      )}
      
      <div className="flex gap-4 justify-center">
        {showRetry && onRetry && (
          <Button onClick={onRetry} variant="primary">
            Try Again
          </Button>
        )}
        
        {showReset && onReset && (
          <Button onClick={onReset} variant="secondary">
            Start Over
          </Button>
        )}
      </div>
    </Card>
  );
}