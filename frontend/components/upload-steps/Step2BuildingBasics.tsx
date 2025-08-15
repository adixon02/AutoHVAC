import React, { useState, memo } from 'react'
import { useDebounce } from '../../hooks/useDebounce'
import { type ProjectData } from './index'

interface Step2Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onNext: () => void
  onPrev: () => void
}

function Step2BuildingBasics({ projectData, updateProjectData, onNext, onPrev }: Step2Props) {
  const [error, setError] = useState('')
  const debouncedSquareFootage = useDebounce(projectData.squareFootage, 500)

  const validateAndNext = () => {
    if (!projectData.squareFootage || projectData.squareFootage.trim() === '') {
      setError('Please enter the square footage of your building')
      return
    }
    
    const sqft = parseFloat(projectData.squareFootage)
    if (isNaN(sqft) || sqft < 200 || sqft > 50000) {
      setError('Please enter a valid square footage between 200 and 50,000 sq ft')
      return
    }
    
    setError('')
    onNext()
  }

  return (
    <div className="space-y-6">
      {/* Square Footage Input - Most Critical Field */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Square Footage <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type="number"
            value={projectData.squareFootage}
            onChange={(e) => updateProjectData({ squareFootage: e.target.value })}
            placeholder="1,853"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors pr-16"
          />
          <span className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm">
            sq ft
          </span>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          💡 This is the most critical measurement for accurate load calculations. Most homes are 1,200-3,000 sq ft.
        </p>
      </div>

      {/* Number of Stories - Simple Selection */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-3">
          Number of Stories
        </label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: '1', label: '1 Story', icon: '🏠' },
            { value: '2', label: '2 Stories', icon: '🏘️' },
            { value: '3+', label: '3+ Stories', icon: '🏢' }
          ].map((option) => (
            <label
              key={option.value}
              className={`relative flex flex-col items-center p-4 border-2 rounded-xl cursor-pointer transition-all ${
                projectData.numberOfStories === option.value
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="numberOfStories"
                value={option.value}
                checked={projectData.numberOfStories === option.value}
                onChange={(e) => updateProjectData({ numberOfStories: e.target.value as any })}
                className="sr-only"
              />
              <span className="text-2xl mb-2">{option.icon}</span>
              <span className="text-sm font-medium text-center">{option.label}</span>
            </label>
          ))}
        </div>
        <p className="mt-2 text-sm text-gray-500">
          🎯 This helps us calculate room-by-room loads and multi-story air distribution accurately.
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Required Information</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 px-6 py-3 border border-gray-300 rounded-xl font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={validateAndNext}
          className="flex-1 btn-primary text-lg py-3"
        >
          Continue →
        </button>
      </div>
    </div>
  )
}

export default memo(Step2BuildingBasics)