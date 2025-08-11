import { useRouter } from 'next/router'

export default function PaymentCancel() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md mx-auto">
        <div className="card glass p-6 text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
            <svg
              className="h-6 w-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <h2 className="display-xs text-gray-900 mb-2">
            Payment Cancelled
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Your payment was cancelled. You can try again anytime.
          </p>
          <button
            onClick={() => router.push('/')}
            className="btn-primary w-full"
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  )
}