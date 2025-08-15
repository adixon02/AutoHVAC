import React, { memo } from 'react'
import { ProjectData } from './index'

interface Step5Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onNext: () => void
  onPrev: () => void
  error: string | null
  setError: (error: string | null) => void
}

function Step5ZipCode({ projectData, updateProjectData, onNext, onPrev, error, setError }: Step5Props) {
  const handleNext = () => {
    if (!projectData.zipCode.trim()) {
      setError('Please enter a ZIP code')
      return
    }
    if (!/^\d{5}$/.test(projectData.zipCode.trim())) {
      setError('ZIP code must be exactly 5 digits')
      return
    }
    setError(null)
    onNext()
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          ZIP Code
        </label>
        <input
          type="text"
          value={projectData.zipCode}
          onChange={(e) => updateProjectData({ zipCode: e.target.value.replace(/\D/g, '').slice(0, 5) })}
          placeholder="12345"
          maxLength={5}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors text-center text-xl font-mono"
        />
        <p className="mt-2 text-sm text-gray-500">
          We use this for accurate climate data and HVAC sizing calculations
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Please Enter ZIP Code</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      <div className="flex space-x-4">
        <button onClick={onPrev} className="flex-1 btn-secondary text-lg py-4">
          Back
        </button>
        <button onClick={handleNext} className="flex-1 btn-primary text-lg py-4">
          Continue
        </button>
      </div>
    </div>
  )
}

export default memo(Step5ZipCode)