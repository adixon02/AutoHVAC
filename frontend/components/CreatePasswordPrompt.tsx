import { useState } from 'react'
import { signIn } from 'next-auth/react'

interface CreatePasswordPromptProps {
  email: string
  onSuccess?: () => void
  onSkip?: () => void
}

export default function CreatePasswordPrompt({ 
  email, 
  onSuccess,
  onSkip 
}: CreatePasswordPromptProps) {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate passwords
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsLoading(true)

    try {
      // Upgrade the account
      const res = await fetch('/api/auth/upgrade-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || 'Failed to create account')
      }

      // Sign in with the new credentials
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      })

      if (result?.ok) {
        onSuccess?.()
      } else {
        throw new Error('Failed to sign in after account creation')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setIsLoading(false)
    }
  }

  if (showForm) {
    return (
      <div className="bg-gradient-to-r from-brand-50 to-blue-50 rounded-lg p-6 border border-brand-200">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-brand-800 mb-2">
              Create Your Password
            </h3>
            <p className="text-sm text-brand-600">
              Secure your account to save all your reports and access them anytime.
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="At least 8 characters"
              required
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Enter password again"
              required
              disabled={isLoading}
            />
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 bg-brand-600 text-white px-4 py-2 rounded-md hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                onSkip?.()
              }}
              disabled={isLoading}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Maybe Later
            </button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-r from-brand-50 to-blue-50 rounded-lg p-6 border border-brand-200">
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <svg className="w-8 h-8 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-brand-800 mb-2">
            Secure Your Account
          </h3>
          <p className="text-sm text-brand-600 mb-4">
            While we analyze your blueprint, create a password to save all your reports 
            and access them anytime. Your email <span className="font-medium">{email}</span> is 
            already registered.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => setShowForm(true)}
              className="bg-brand-600 text-white px-4 py-2 rounded-md hover:bg-brand-700 transition-colors text-sm font-medium"
            >
              Create Password
            </button>
            <button
              onClick={onSkip}
              className="text-gray-600 hover:text-gray-800 transition-colors text-sm"
            >
              Skip for Now
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}