import React, { useState } from 'react'
import { apiClient } from '../lib/api-client'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/router'

interface CompletionAccountGateProps {
  email: string
  jobResult?: {
    total_sqft?: number
    heating_load_btu_hr?: number
    cooling_load_btu_hr?: number
    room_count?: number
    equipment_recommendations?: any[]
  }
  onSuccess: () => void
}

export default function CompletionAccountGate({
  email,
  jobResult,
  onSuccess,
}: CompletionAccountGateProps) {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()

  // Extract stats from job result for teaser
  const stats = {
    sqft: jobResult?.total_sqft || 2847,
    heatingLoad: jobResult?.heating_load_btu_hr || 73240,
    coolingLoad: jobResult?.cooling_load_btu_hr || 67890,
    rooms: jobResult?.room_count || 12,
    equipment: jobResult?.equipment_recommendations?.length || 3
  }

  const validatePassword = () => {
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return false
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return false
    }
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!validatePassword()) {
      return
    }

    setIsLoading(true)

    try {
      // Convert lead to user
      const response = await apiClient.convertLeadToUser({
        email,
        password,
      })

      if (response.success) {
        // Sign in with the new credentials
        const signInResult = await signIn('credentials', {
          email,
          password,
          redirect: false,
        })

        if (signInResult?.ok) {
          // Success - hide gate and show results on current page
          onSuccess()
          // Don't redirect - let them see their results on the analyzing page
        } else {
          setError('Account created but sign-in failed. Please try signing in manually.')
        }
      }
    } catch (err: any) {
      console.error('Account creation error:', err)
      setError(err.message || 'Failed to create account. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSkip = () => {
    // For now, just redirect to home
    // In production, might want to save the state somehow
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Success Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-success-100 rounded-full mb-4">
            <svg className="w-8 h-8 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            🎉 Your Professional HVAC Analysis is Complete!
          </h1>
          <p className="text-lg text-gray-600">
            We've calculated everything you need for your project
          </p>
        </div>

        {/* Blurred Preview Card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden mb-8 relative">
          {/* Blur overlay */}
          <div className="absolute inset-0 backdrop-blur-sm bg-white/30 z-10 flex items-center justify-center">
            <div className="text-center">
              <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <p className="text-gray-600 font-medium">Create account to unlock</p>
            </div>
          </div>
          
          {/* Preview content (blurred) */}
          <div className="p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Analysis Results</h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Area Analyzed:</span>
                  <span className="font-mono font-bold">█,███ sq ft</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Heating Load:</span>
                  <span className="font-mono font-bold">██,███ BTU/hr</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Cooling Load:</span>
                  <span className="font-mono font-bold">██,███ BTU/hr</span>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Rooms Analyzed:</span>
                  <span className="font-mono font-bold">██ rooms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Equipment Options:</span>
                  <span className="font-mono font-bold">█ recommendations</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Report Status:</span>
                  <span className="text-success-600 font-bold">✅ Ready</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Account Creation Form */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              🔓 Create your FREE account to unlock:
            </h2>
            <div className="grid md:grid-cols-2 gap-4 mt-4 text-left">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-700">Complete room-by-room breakdown</span>
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-700">Professional PDF report</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-700">Equipment sizing recommendations</span>
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-700">Save to your dashboard forever</span>
                </div>
              </div>
            </div>
          </div>

          {/* No Credit Card Required Banner */}
          <div className="bg-gradient-to-r from-success-50 to-brand-50 border border-success-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-center gap-3">
              <svg className="w-6 h-6 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <div className="text-center">
                <p className="font-bold text-success-800">💳 No credit card required</p>
                <p className="text-sm text-success-700">Your first report is completely FREE!</p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Field (Locked) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                disabled
                className="w-full px-3 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-600"
              />
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Create Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                required
                minLength={8}
              />
            </div>

            {/* Confirm Password Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                required
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-error-50 border border-error-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-error-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm text-error-600">{error}</p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 bg-gradient-to-r from-brand-600 to-brand-700 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:from-brand-700 hover:to-brand-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Creating Account...
                  </span>
                ) : (
                  '🔓 Create FREE Account & Unlock Report'
                )}
              </button>
              
              <button
                type="button"
                onClick={handleSkip}
                className="px-6 py-3 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Skip for now
              </button>
            </div>

            {/* Terms */}
            <p className="text-xs text-center text-gray-500">
              By creating an account, you agree to our{' '}
              <a href="/terms" className="text-brand-600 hover:underline">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="/privacy" className="text-brand-600 hover:underline">
                Privacy Policy
              </a>
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}