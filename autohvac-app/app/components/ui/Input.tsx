'use client';

import { InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error = false, leftIcon, rightIcon, className = '', ...props }, ref) => {
    const baseClasses = 'w-full px-4 py-3 bg-white border rounded-xl transition-all duration-200 ease-out focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder:text-neutral-400 text-neutral-800 font-medium shadow-soft focus:shadow-medium';
    const errorClasses = error 
      ? 'border-error-300 focus:ring-error-500 focus:border-error-500' 
      : 'border-neutral-300 focus:ring-primary-500 focus:border-primary-500 hover:border-neutral-400';
    
    const inputClasses = `${baseClasses} ${errorClasses} ${
      leftIcon ? 'pl-10' : ''
    } ${rightIcon ? 'pr-10' : ''} ${className}`;

    if (leftIcon || rightIcon) {
      return (
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-400">{leftIcon}</span>
            </div>
          )}
          
          <input
            ref={ref}
            className={inputClasses}
            {...props}
          />
          
          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span className="text-gray-400">{rightIcon}</span>
            </div>
          )}
        </div>
      );
    }

    return (
      <input
        ref={ref}
        className={inputClasses}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

export default Input;