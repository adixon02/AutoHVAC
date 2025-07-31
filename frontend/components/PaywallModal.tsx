import React, { useState } from 'react'
import { apiHelpers } from '../lib/fetcher'

interface PaywallModalProps {
  isOpen: boolean
  onClose: () => void
  userEmail: string
}

export default function PaywallModal({ isOpen, onClose, userEmail }: PaywallModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleUpgrade = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiHelpers.createCheckoutSession(userEmail)
      
      if (response.checkout_url) {
        // Redirect to Stripe checkout
        window.location.href = response.checkout_url
      } else {
        console.error('Response received:', response)
        throw new Error('No checkout URL received')
      }
    } catch (err: any) {
      console.error('Upgrade error:', err)
      console.error('Error details:', err.response?.data)
      
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to start upgrade process'
      setError(errorMessage)
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-8 pb-0">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-3xl font-bold text-brand-700">
                You've Used Your Free Report!
              </h2>
              <p className="text-lg text-gray-600 mt-2">
                Unlock unlimited HVAC load calculations and advanced features with Pro
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={isLoading}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Pricing Section */}
        <div className="p-8">
          <div className="bg-gradient-to-br from-brand-50 to-brand-100 rounded-2xl p-8 mb-8">
            <div className="text-center">
              <p className="text-brand-600 font-semibold text-lg mb-2">AutoHVAC Pro</p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-5xl font-bold text-brand-700">$97</span>
                <span className="text-xl text-brand-600">/month</span>
              </div>
              <p className="text-brand-600 mt-2">Cancel anytime</p>
            </div>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div>
              <h3 className="font-semibold text-brand-700 mb-4">What's Included:</h3>
              <ul className="space-y-3">
                {[
                  'Unlimited HVAC load calculations',
                  'PDF report downloads',
                  'Advanced duct design tools',
                  'Equipment recommendations',
                  'Climate data for any location',
                  'Priority support',
                  'API access (coming soon)'
                ].map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-brand-700 mb-4">Perfect For:</h3>
              <ul className="space-y-3">
                {[
                  'HVAC contractors',
                  'Mechanical engineers',
                  'Building designers',
                  'Energy consultants',
                  'Anyone doing 3+ projects/month'
                ].map((useCase, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-brand-500">•</span>
                    <span className="text-gray-700">{useCase}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Testimonials */}
          <div className="bg-gray-50 rounded-xl p-6 mb-8">
            <p className="text-gray-700 italic mb-3">
              "AutoHVAC saved me hours on every project. The accuracy is incredible and my clients love the professional reports."
            </p>
            <p className="text-sm text-gray-600 font-semibold">
              — Mike S., HVAC Contractor
            </p>
          </div>

          {/* CTA */}
          <div className="text-center">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}
            
            <button
              onClick={handleUpgrade}
              disabled={isLoading}
              className="btn-primary text-lg px-8 py-4 w-full md:w-auto"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing...
                </span>
              ) : (
                'Upgrade to Pro'
              )}
            </button>

            <p className="text-sm text-gray-500 mt-4">
              Secure payment via Stripe • Cancel anytime
            </p>
          </div>
        </div>

        {/* Comparison Table (optional) */}
        <div className="border-t border-gray-200 p-8 bg-gray-50">
          <h3 className="font-semibold text-brand-700 mb-4 text-center">Free vs Pro Comparison</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div></div>
            <div className="text-center font-semibold text-gray-600">Free</div>
            <div className="text-center font-semibold text-brand-700">Pro</div>
            
            {[
              ['Reports per month', '1', 'Unlimited'],
              ['PDF downloads', '✓', '✓'],
              ['Report sharing', '✓', '✓'],
              ['Advanced features', '✗', '✓'],
              ['Priority support', '✗', '✓'],
              ['API access', '✗', 'Coming soon']
            ].map(([feature, free, pro], idx) => (
              <React.Fragment key={idx}>
                <div className="text-gray-700">{feature}</div>
                <div className="text-center text-gray-600">{free}</div>
                <div className="text-center text-brand-700 font-semibold">{pro}</div>
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}