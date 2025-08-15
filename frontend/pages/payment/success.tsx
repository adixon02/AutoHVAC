import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import { useSession } from 'next-auth/react'
import Head from 'next/head'

export default function PaymentSuccess() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const { session_id } = router.query
  const [countdown, setCountdown] = useState(5)
  const [userEmail, setUserEmail] = useState<string>('')
  const [needsAccount, setNeedsAccount] = useState(false)

  // Get email from Stripe session
  useEffect(() => {
    if (session_id && status !== 'loading') {
      // Fetch the Stripe session to get customer email
      fetch(`/api/stripe/session/${session_id}`)
        .then(res => res.json())
        .then(data => {
          if (data.customer_email) {
            setUserEmail(data.customer_email)
            // If no NextAuth session but we have payment, user needs account
            setNeedsAccount(!session)
          }
        })
        .catch(err => console.error('Failed to fetch session:', err))
    }
  }, [session_id, session, status])

  useEffect(() => {
    // Only start countdown if we don't need account creation
    if (!needsAccount && userEmail) {
      const interval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(interval)
            router.push('/dashboard')
            return 0
          }
          return prev - 1
        })
      }, 1000)
      
      return () => clearInterval(interval)
    }
  }, [router, needsAccount, userEmail])

  return (
    <>
      <Head>
        <title>Welcome to AutoHVAC Pro! - AutoHVAC</title>
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="card glass p-8 text-center">
            {/* Success Icon */}
            <div className="w-20 h-20 bg-gradient-to-r from-green-400 to-green-600 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            
            {/* Success Message */}
            <h1 className="display-md text-gray-900 mb-2">
              {needsAccount ? 'Payment Successful!' : 'Welcome to AutoHVAC Pro!'}
            </h1>
            <p className="text-gray-600 mb-8">
              {needsAccount 
                ? 'Your subscription is active! Create an account to access your Pro features.'
                : 'Your subscription is now active. You have unlimited access to all Pro features.'
              }
            </p>
            
            {/* What's Included */}
            <div className="bg-gradient-to-r from-brand-50 to-brand-25 rounded-xl p-6 mb-6">
              <h2 className="font-semibold text-gray-900 mb-3">What you can do now:</h2>
              <ul className="space-y-2 text-left">
                {[
                  'Upload unlimited blueprints',
                  'Generate professional PDF reports',
                  'Access advanced HVAC calculations',
                  'Get equipment recommendations',
                  'Priority processing for all projects'
                ].map((feature, idx) => (
                  <li key={idx} className="flex items-start text-sm text-gray-700">
                    <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
            
            {/* Conditional Content Based on Account Status */}
            {needsAccount ? (
              // User needs to create account
              <div className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
                  <h3 className="font-semibold text-blue-900 mb-2">Complete Your Setup</h3>
                  <p className="text-sm text-blue-800 mb-4">
                    Your payment was successful and your Pro subscription is active for <strong>{userEmail}</strong>. 
                    Create an account to access your dashboard and start uploading blueprints.
                  </p>
                  <button
                    onClick={() => router.push(`/auth/signup?email=${encodeURIComponent(userEmail)}&plan=pro`)}
                    className="w-full btn-primary"
                  >
                    Create Account & Access Dashboard
                  </button>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-2">
                    Already have an account with this email?
                  </p>
                  <button
                    onClick={() => router.push(`/auth/signin?callbackUrl=/dashboard&email=${encodeURIComponent(userEmail)}`)}
                    className="text-brand-600 hover:text-brand-700 font-medium text-sm"
                  >
                    Sign in instead
                  </button>
                </div>
              </div>
            ) : (
              // User has account, show countdown
              <div className="space-y-6">
                <div className="mb-6">
                  <p className="text-sm text-gray-600 mb-2">
                    Redirecting to your dashboard in
                  </p>
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-100 rounded-full">
                    <span className="text-2xl font-bold text-brand-600">
                      {countdown}
                    </span>
                  </div>
                </div>
                
                <button
                  onClick={() => router.push('/dashboard')}
                  className="w-full btn-primary btn-lg"
                >
                  Go to Dashboard Now
                </button>
              </div>
            )}
            
            {/* Quick Actions */}
            <div className="mt-6 pt-6 border-t">
              <p className="text-sm text-gray-600 mb-3">Quick actions:</p>
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => router.push('/dashboard?upload=true')}
                  className="text-sm text-brand-600 hover:text-brand-700 font-medium"
                >
                  Upload Blueprint
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => router.push('/billing')}
                  className="text-sm text-brand-600 hover:text-brand-700 font-medium"
                >
                  View Billing
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}