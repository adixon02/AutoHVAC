import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import Head from 'next/head'
import axios from 'axios'

export default function SignUp() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [passwordStrength, setPasswordStrength] = useState({
    hasLower: false,
    hasUpper: false,
    hasNumber: false,
    hasSpecial: false,
    hasLength: false,
  })
  
  // Pre-fill email from query params and handle redirect
  useEffect(() => {
    if (status === 'authenticated') {
      router.push('/dashboard')
    }
    
    // Pre-fill email if coming from payment success
    if (router.query.email && typeof router.query.email === 'string') {
      setEmail(router.query.email)
    }
  }, [status, router])
  
  // Check password strength
  useEffect(() => {
    setPasswordStrength({
      hasLower: /[a-z]/.test(password),
      hasUpper: /[A-Z]/.test(password),
      hasNumber: /[0-9]/.test(password),
      hasSpecial: /[^A-Za-z0-9]/.test(password),
      hasLength: password.length >= 8,
    })
  }, [password])
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    
    // Validate password strength
    const { hasLower, hasUpper, hasNumber, hasSpecial, hasLength } = passwordStrength
    if (!(hasLower && hasUpper && hasNumber && hasSpecial && hasLength)) {
      setError('Password does not meet all requirements')
      return
    }
    
    setLoading(true)
    
    try {
      const response = await axios.post('/api/auth/signup', {
        email,
        password,
        name,
      })
      
      if (response.data.success) {
        setSuccess(true)
      }
    } catch (err: any) {
      if (err.response?.data?.error) {
        setError(err.response.data.error)
      } else {
        setError('An error occurred during signup. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }
  
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
      </div>
    )
  }
  
  if (success) {
    return (
      <>
        <Head>
          <title>Verify Your Email - AutoHVAC</title>
        </Head>
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25 flex items-center justify-center p-4">
          <div className="max-w-md w-full">
            <div className="card glass p-8 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="display-xs text-gray-900 mb-2">Account Created!</h2>
              <p className="text-gray-600 mb-6">
                Please check your email at <strong className="text-gray-900">{email}</strong> to verify your account.
              </p>
              <p className="text-sm text-gray-500 mb-4">
                We sent you a verification link. Click it to activate your account and start using AutoHVAC.
              </p>
              <Link 
                href="/auth/signin" 
                className="inline-block mt-4 text-brand-600 hover:text-brand-500 font-medium"
              >
                Go to Sign In →
              </Link>
            </div>
          </div>
        </div>
      </>
    )
  }
  
  return (
    <>
      <Head>
        <title>Sign Up - AutoHVAC</title>
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="card glass p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="display-md gradient-text">
                Create Your Account
              </h1>
              <p className="text-gray-600 mt-2">
                Start with your first free HVAC calculation
              </p>
            </div>
            
            {/* Error Message */}
            {error && (
              <div className="mb-6 alert alert-error">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}
            
            {/* Sign Up Form */}
            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input"
                    placeholder="John Doe"
                  />
                </div>
                
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="input"
                    placeholder="you@example.com"
                  />
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="input"
                    placeholder="••••••••"
                  />
                  
                  {/* Password Strength Indicator */}
                  {password && (
                    <div className="mt-2 space-y-1">
                      <div className="text-xs font-medium text-gray-700 mb-1">Password requirements:</div>
                      <div className={`text-xs flex items-center ${passwordStrength.hasLength ? 'text-green-600' : 'text-gray-400'}`}>
                        {passwordStrength.hasLength ? '✓' : '○'} At least 8 characters
                      </div>
                      <div className={`text-xs flex items-center ${passwordStrength.hasUpper ? 'text-green-600' : 'text-gray-400'}`}>
                        {passwordStrength.hasUpper ? '✓' : '○'} One uppercase letter
                      </div>
                      <div className={`text-xs flex items-center ${passwordStrength.hasLower ? 'text-green-600' : 'text-gray-400'}`}>
                        {passwordStrength.hasLower ? '✓' : '○'} One lowercase letter
                      </div>
                      <div className={`text-xs flex items-center ${passwordStrength.hasNumber ? 'text-green-600' : 'text-gray-400'}`}>
                        {passwordStrength.hasNumber ? '✓' : '○'} One number
                      </div>
                      <div className={`text-xs flex items-center ${passwordStrength.hasSpecial ? 'text-green-600' : 'text-gray-400'}`}>
                        {passwordStrength.hasSpecial ? '✓' : '○'} One special character
                      </div>
                    </div>
                  )}
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
                    required
                    className="input"
                    placeholder="••••••••"
                  />
                  {confirmPassword && password !== confirmPassword && (
                    <p className="text-xs text-red-600 mt-1">Passwords do not match</p>
                  )}
                </div>
              </div>
              
              <div className="mt-6">
                <p className="text-xs text-gray-600">
                  By creating an account, you agree to our{' '}
                  <Link href="/terms" className="text-brand-600 hover:text-brand-500">
                    Terms of Service
                  </Link>{' '}
                  and{' '}
                  <Link href="/privacy" className="text-brand-600 hover:text-brand-500">
                    Privacy Policy
                  </Link>
                </p>
              </div>
              
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-6 btn-primary btn-lg"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating account...
                  </span>
                ) : (
                  'Create Account'
                )}
              </button>
            </form>
            
            {/* Benefits */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="text-sm text-gray-600 space-y-2">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>First HVAC calculation completely free</span>
                </div>
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>Professional ACCA Manual J reports</span>
                </div>
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>Cancel anytime, no commitment</span>
                </div>
              </div>
            </div>
            
            {/* Sign In Link */}
            <p className="mt-6 text-center text-sm text-gray-600">
              Already have an account?{' '}
              <Link href="/auth/signin" className="font-medium text-brand-600 hover:text-brand-500">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </>
  )
}