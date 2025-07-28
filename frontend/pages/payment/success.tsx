import { useEffect } from 'react'
import { useRouter } from 'next/router'

export default function PaymentSuccess() {
  const router = useRouter()
  const { session_id } = router.query

  useEffect(() => {
    if (session_id) {
      setTimeout(() => {
        router.push('/')
      }, 3000)
    }
  }, [session_id, router])

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
          <p className="text-xs text-gray-500">
            Redirecting you back to the main page...
          </p>
        </div>
      </div>
    </div>
  )
}