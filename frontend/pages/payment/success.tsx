import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import { useSession } from 'next-auth/react'
import Head from 'next/head'

export default function PaymentSuccess() {
  const router = useRouter()
  const { data: session } = useSession()
  const { session_id } = router.query
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    // Countdown timer
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
    
    // Cleanup on unmount
    return () => clearInterval(interval)
  }, [router])

  return (
    <>
      <Head>
        <title>Welcome to AutoHVAC Pro! - AutoHVAC</title>
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            {/* Success Icon */}
            <div className="w-20 h-20 bg-gradient-to-r from-green-400 to-green-600 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            
            {/* Success Message */}
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome to AutoHVAC Pro!
            </h1>
            <p className="text-gray-600 mb-8">
              Your subscription is now active. You have unlimited access to all Pro features.
            </p>
            
            {/* What's Included */}
            <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-6 mb-6">
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
            
            {/* Countdown */}
            <div className="mb-6">
              <p className="text-sm text-gray-600 mb-2">
                Redirecting to your dashboard in
              </p>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-full">
                <span className="text-2xl font-bold text-indigo-600">
                  {countdown}
                </span>
              </div>
            </div>
            
            {/* CTA Button */}
            <button
              onClick={() => router.push('/dashboard')}
              className="w-full py-3 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all"
            >
              Go to Dashboard Now
            </button>
            
            {/* Quick Actions */}
            <div className="mt-6 pt-6 border-t">
              <p className="text-sm text-gray-600 mb-3">Quick actions:</p>
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => router.push('/dashboard?upload=true')}
                  className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  Upload Blueprint
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => router.push('/billing')}
                  className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
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