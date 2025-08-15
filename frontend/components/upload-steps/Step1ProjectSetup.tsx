import React, { useState, memo } from 'react'
import { useDebounce } from '../../hooks/useDebounce'
import { type ProjectData } from './index'

interface Step1Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onNext: () => void
  error: string | null
  setError: (error: string | null) => void
}

function Step1ProjectSetup({ projectData, updateProjectData, onNext, error, setError }: Step1Props) {
  const debouncedProjectName = useDebounce(projectData.projectName, 300)
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      updateProjectData({ blueprintFile: e.target.files[0] })
    }
  }

  const handleNext = () => {
    if (!projectData.projectName.trim()) {
      setError('Please enter a project name')
      return
    }
    if (!projectData.blueprintFile) {
      setError('Please select a blueprint file')
      return
    }
    setError(null)
    onNext()
  }

  return (
    <div className="space-y-6">
      {/* Project Name */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Project Name
        </label>
        <input
          type="text"
          value={projectData.projectName}
          onChange={(e) => updateProjectData({ projectName: e.target.value })}
          placeholder="e.g., Smith Residence, Downtown Office Building"
          maxLength={255}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
        />
        <p className="mt-2 text-sm text-gray-500">
          This helps you identify the project in your dashboard
        </p>
      </div>

      {/* Blueprint Upload */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Blueprint File
        </label>
        <div className="relative">
          <input
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.png,.jpg,.jpeg"
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="w-full border-2 border-dashed border-brand-200 rounded-xl p-8 text-center hover:border-brand-500 transition-colors cursor-pointer block"
          >
            {projectData.blueprintFile ? (
              <div className="flex items-center justify-center">
                <svg className="w-8 h-8 text-brand-700 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-brand-700 font-medium">{projectData.blueprintFile.name}</span>
              </div>
            ) : (
              <div>
                <svg className="w-12 h-12 text-brand-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-brand-700 font-medium mb-2">
                  Drop your blueprint here or click to browse
                </p>
                <p className="text-gray-500 text-sm">
                  Supports PDF, PNG, JPG, JPEG files (max 50MB)
                </p>
              </div>
            )}
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Please Complete Setup</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Continue Button */}
      <button
        onClick={handleNext}
        className="w-full btn-primary text-lg py-4"
      >
        Continue
      </button>
    </div>
  )
}

export default memo(Step1ProjectSetup)