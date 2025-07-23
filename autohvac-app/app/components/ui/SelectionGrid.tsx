'use client';

import { ReactNode } from 'react';

interface SelectionOption {
  value: string;
  title: string;
  description?: string;
  icon?: ReactNode;
}

interface SelectionGridProps {
  options: SelectionOption[];
  selectedValue: string;
  onSelect: (value: string) => void;
  columns?: 2 | 3 | 4;
  className?: string;
}

export default function SelectionGrid({ 
  options, 
  selectedValue, 
  onSelect, 
  columns = 2,
  className = '' 
}: SelectionGridProps) {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4'
  };

  return (
    <div className={`grid ${gridCols[columns]} gap-4 ${className}`}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`p-6 rounded-xl border-2 transition-all duration-200 ease-out text-left shadow-soft hover:shadow-medium transform hover:scale-[1.02] ${
            selectedValue === option.value
              ? 'border-primary-500 bg-primary-50 shadow-medium ring-2 ring-primary-200' 
              : 'border-neutral-300 hover:border-neutral-400 bg-white hover:bg-neutral-50'
          }`}
          onClick={() => onSelect(option.value)}
        >
          {option.icon && (
            <div className="mb-3 text-primary-600 flex items-center justify-center w-8 h-8">
              {option.icon}
            </div>
          )}
          
          <div className="font-semibold text-neutral-900 mb-2 text-lg">
            {option.title}
          </div>
          
          {option.description && (
            <div className="text-sm text-neutral-600 leading-relaxed">
              {option.description}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}