import React from 'react';

export interface HeaderProps {
  title?: string;
  subtitle?: string;
}

const Header: React.FC<HeaderProps> = ({ 
  title = "AutoHVAC", 
  subtitle = "Professional HVAC Load Calculations" 
}) => {
  return (
    <header className="bg-white/95 backdrop-blur-lg border-b border-gray-200/50 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex items-center">
                {/* Premium Logo */}
                <div className="relative h-10 w-10 premium-gradient rounded-xl flex items-center justify-center shadow-lg">
                  <svg
                    className="h-6 w-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
                    />
                  </svg>
                  <div className="absolute -inset-1 premium-gradient rounded-xl blur opacity-25"></div>
                </div>
                
                <div className="ml-4">
                  <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
                    {title}
                    <span className="text-blue-600 ml-1">Pro</span>
                  </h1>
                  {subtitle && (
                    <p className="text-sm professional-text font-medium">{subtitle}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
          
          {/* Right side - Professional badges */}
          <div className="flex items-center space-x-6">
            <div className="hidden sm:flex items-center space-x-4">
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <span>AI-Powered</span>
              </div>
              <div className="text-xs font-medium text-gray-500 px-3 py-1.5 bg-gray-100 rounded-full">
                ACCA Manual J
              </div>
            </div>
            
            <div className="flex items-center space-x-2 text-sm">
              <span className="font-medium text-gray-600">v2.0</span>
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export { Header };