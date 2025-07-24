import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'gradient';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = 'primary', 
    size = 'md', 
    loading = false, 
    disabled, 
    children, 
    icon,
    iconPosition = 'left',
    ...props 
  }, ref) => {
    const baseStyles = 'premium-button inline-flex items-center justify-center font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none disabled:cursor-not-allowed relative overflow-hidden';
    
    const variants = {
      primary: 'premium-gradient text-white shadow-lg hover:shadow-xl focus-visible:ring-blue-500 border-0',
      secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus-visible:ring-gray-500 border border-gray-200',
      outline: 'border-2 border-gray-300 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400 focus-visible:ring-blue-500',
      ghost: 'text-gray-700 hover:bg-gray-100 hover:text-gray-900 focus-visible:ring-blue-500',
      gradient: 'premium-gradient text-white shadow-lg hover:shadow-xl focus-visible:ring-blue-500 border-0 relative before:absolute before:inset-0 before:bg-gradient-to-r before:from-white/20 before:to-transparent before:opacity-0 hover:before:opacity-100 before:transition-opacity before:duration-200',
    };
    
    const sizes = {
      sm: 'h-9 px-4 text-sm gap-2',
      md: 'h-11 px-6 text-sm gap-2',
      lg: 'h-12 px-8 text-base gap-3',
      xl: 'h-14 px-10 text-lg gap-3',
    };
    
    return (
      <button
        ref={ref}
        className={cn(
          baseStyles,
          variants[variant],
          sizes[size],
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        
        {!loading && icon && iconPosition === 'left' && (
          <span className="flex-shrink-0">{icon}</span>
        )}
        
        <span className="relative z-10">{children}</span>
        
        {!loading && icon && iconPosition === 'right' && (
          <span className="flex-shrink-0">{icon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };