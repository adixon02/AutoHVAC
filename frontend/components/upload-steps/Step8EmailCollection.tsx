import React, { memo } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/router'
import { apiClient } from '../../lib/api-client'
import { type ProjectData } from './index'

interface Step8Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onPrev: () => void
  onSubmit: () => void
  isLoading: boolean
  error: string | null
  setError: (error: string | null) => void
}

function Step8EmailCollection({ 
  projectData, 
  updateProjectData, 
  onPrev, 
  onSubmit, 
  isLoading, 
  error, 
  setError 
}: Step8Props) {
  const { data: session } = useSession()
  const router = useRouter()
  const savedEmail = session?.user?.email || ''
  const isReturningUser = savedEmail && savedEmail === projectData.email
  
  const handleSubmit = async () => {
    if (!projectData.email.trim()) {
      setError('Please enter your email address')
      return
    }
    if (!/\S+@\S+\.\S+/.test(projectData.email)) {
      setError('Please enter a valid email address')
      return
    }
    setError(null)
    
    try {
      await apiClient.captureLead({
        email: projectData.email,
        marketing_consent: true,
        project_id: undefined
      })
      
      onSubmit()
    } catch (err: any) {
      console.error('Lead capture error:', err)
      setError('Failed to process email. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      {/* Welcome Back Message */}
      {isReturningUser && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-sm font-medium text-green-800">Welcome back!</h4>
              <p className="text-sm text-green-700 mt-1">
                We've pre-filled your email. Just click continue to proceed.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Email Input */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Email Address
        </label>
        <input
          type="email"
          value={projectData.email}
          onChange={(e) => updateProjectData({ email: e.target.value })}
          placeholder="your@email.com"
          className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
        />
        <p className="mt-2 text-sm text-gray-500">
          {isReturningUser 
            ? '🎉 As a returning user, you know the drill! We\'ll email your analysis when it\'s ready.'
            : '✨ Your first blueprint analysis is completely free! No password or verification required.'
          }
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
              <h4 className="text-sm font-medium text-red-800 mb-1">Please Complete</h4>
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
          onClick={handleSubmit}
          disabled={isLoading}
          className="flex-1 btn-primary text-lg py-3"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            'Start Analysis'
          )}
        </button>
      </div>
    </div>
  )
}

export default memo(Step8EmailCollection)