'use client';

import { ReactNode } from 'react';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  showLogo?: boolean;
}

export default function Header({ 
  title = "AutoHVAC Pro",
  subtitle = "Professional HVAC Load Calculations & System Design",
  actions,
  showLogo = true 
}: HeaderProps) {
  return (
    <header className="bg-white border-b border-neutral-200 shadow-soft sticky top-0 z-50 backdrop-blur-sm bg-white/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          
          {/* Logo and Brand */}
          <div className="flex items-center space-x-4">
            {showLogo && (
              <div className="flex items-center space-x-3">
                {/* HVAC Icon */}
                <div className="w-10 h-10 lg:w-12 lg:h-12 bg-gradient-to-br from-primary-600 to-primary-700 rounded-xl flex items-center justify-center shadow-medium">
                  <svg className="w-6 h-6 lg:w-7 lg:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
                
                {/* Brand Text */}
                <div className="hidden sm:block">
                  <h1 className="text-xl lg:text-2xl font-bold text-neutral-900 leading-tight">
                    {title}
                  </h1>
                  {subtitle && (
                    <p className="text-sm text-neutral-600 font-medium">
                      {subtitle}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Mobile Brand (when logo is hidden or on small screens) */}
          <div className="sm:hidden flex-1">
            <h1 className="text-lg font-bold text-neutral-900 text-center">
              AutoHVAC Pro
            </h1>
          </div>

          {/* Actions */}
          {actions && (
            <div className="flex items-center space-x-3">
              {actions}
            </div>
          )}

          {/* Status/Help Button */}
          <div className="flex items-center space-x-2">
            <div className="hidden lg:flex items-center space-x-2 text-sm text-neutral-600">
              <div className="w-2 h-2 bg-success-500 rounded-full"></div>
              <span className="font-medium">System Online</span>
            </div>
            
            <button className="p-2 text-neutral-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-all duration-200">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}