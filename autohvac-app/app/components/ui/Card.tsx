'use client';

import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  shadow?: 'none' | 'soft' | 'medium' | 'strong';
  hover?: boolean;
  glass?: boolean;
}

export default function Card({ 
  children, 
  className = '', 
  padding = 'md',
  shadow = 'soft',
  hover = false,
  glass = false
}: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-10'
  };

  const shadowClasses = {
    none: '',
    soft: 'shadow-soft',
    medium: 'shadow-medium',
    strong: 'shadow-strong'
  };

  const baseClasses = glass 
    ? 'bg-white/80 backdrop-blur-md border border-white/20 rounded-2xl'
    : 'bg-white border border-neutral-200/50 rounded-2xl';

  const hoverClasses = hover ? 'hover:shadow-medium transition-all duration-300 ease-out hover:transform hover:scale-[1.01]' : '';

  return (
    <div className={`
      ${baseClasses}
      ${paddingClasses[padding]} 
      ${shadowClasses[shadow]} 
      ${hoverClasses}
      ${className}
    `}>
      {children}
    </div>
  );
}