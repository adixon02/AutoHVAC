import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import Cookies from 'js-cookie'

export default function PaymentSuccess() {
  const router = useRouter()
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
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md mx-auto">
        <div className="bg-white shadow rounded-lg p-6 text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
            <svg
              className="h-6 w-6 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="text-lg font-medium text-gray-900 mb-2">
            Payment Successful!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Your subscription is now active. You can upload unlimited blueprints.
          </p>
          <div className="mb-6">
            <p className="text-sm text-gray-600 mb-2">
              Redirecting you to your dashboard in
            </p>
            <div className="text-3xl font-bold text-brand-600 mb-2">
              {countdown}
            </div>
            <p className="text-xs text-gray-500">
              seconds
            </p>
          </div>
          <a 
            href="/dashboard" 
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-brand-600 hover:bg-brand-700 transition-colors"
          >
            Go to Dashboard Now
          </a>
        </div>
      </div>
    </div>
  )
}