import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import { apiHelpers } from '../lib/fetcher'
import Cookies from 'js-cookie'

export default function Upgrade() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [stripeUnavailable, setStripeUnavailable] = useState(false)

  useEffect(() => {
    // Get email from cookie
    const email = Cookies.get('user_email')
    if (email) {
      setUserEmail(email)
    }
  }, [])

  const handleUpgrade = async () => {
    if (!userEmail) {
      setError('Please log in to continue')
      return
    }

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
      
      // Check if this is a Stripe availability issue
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to start upgrade process'
      
      if (errorMessage.toLowerCase().includes('stripe') || 
          errorMessage.toLowerCase().includes('payment system') ||
          errorMessage.toLowerCase().includes('authentication')) {
        setStripeUnavailable(true)
        setError(errorMessage)
      } else {
        setError(errorMessage)
      }
      
      setIsLoading(false)
    }
  }

  return (
    <>
      <Head>
        <title>Upgrade to Pro - AutoHVAC</title>
        <meta name="description" content="Unlock unlimited HVAC load calculations and advanced features" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Simple Header */}
        <nav className="bg-white shadow-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="text-2xl font-bold text-brand-700 cursor-pointer" onClick={() => router.push('/')}>
                AutoHVAC
              </div>
              {userEmail && (
                <span className="text-sm text-gray-600">{userEmail}</span>
              )}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              You've Used Your Free Analysis! 🎉
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Great news - your first HVAC load calculation is complete. 
              Upgrade to Pro to continue analyzing blueprints and unlock advanced features.
            </p>
          </div>

          {/* Pricing Card */}
          <div className="bg-white rounded-2xl shadow-xl p-8 mb-12">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-brand-700 mb-2">AutoHVAC Pro</h2>
              <div className="flex items-baseline justify-center gap-2">
                <span className="text-5xl font-bold text-gray-900">$97</span>
                <span className="text-xl text-gray-600">/month</span>
              </div>
              <p className="text-gray-600 mt-2">Cancel anytime • No setup fees</p>
            </div>

            {/* Features Grid */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div>
                <h3 className="font-semibold text-gray-900 mb-4">Everything You Get:</h3>
                <ul className="space-y-3">
                  {[
                    'Unlimited HVAC load calculations',
                    'Instant PDF report downloads',
                    'Advanced duct sizing tools',
                    'Equipment recommendations',
                    'Climate data for any US location',
                    'Priority email support',
                    'New features as we ship them'
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
                <h3 className="font-semibold text-gray-900 mb-4">Perfect For:</h3>
                <ul className="space-y-3">
                  {[
                    'HVAC contractors & installers',
                    'Mechanical engineers',
                    'Building designers & architects',
                    'Energy consultants',
                    'Home performance professionals',
                    'Anyone doing 3+ projects/month'
                  ].map((useCase, idx) => (
                    <li key={idx} className="flex items-start gap-3">
                      <span className="text-brand-600 mt-0.5">→</span>
                      <span className="text-gray-700">{useCase}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* CTA */}
            <div className="text-center">
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}
              
              {stripeUnavailable ? (
                <>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
                    <h3 className="font-semibold text-yellow-800 mb-2">
                      Payment System Temporarily Unavailable
                    </h3>
                    <p className="text-yellow-700 mb-4">
                      We're experiencing a temporary issue with our payment processor. 
                      Please try again in a few minutes, or contact our support team for assistance.
                    </p>
                    <div className="space-y-3">
                      <button
                        onClick={() => {
                          setStripeUnavailable(false)
                          setError(null)
                        }}
                        className="btn-secondary w-full"
                      >
                        Try Again
                      </button>
                      <a
                        href={`mailto:support@autohvac.com?subject=Upgrade%20Request&body=Hi,%20I'd%20like%20to%20upgrade%20to%20Pro.%20My%20email%20is:%20${userEmail || ''}`}
                        className="btn-primary w-full inline-block"
                      >
                        Contact Support
                      </a>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <button
                    onClick={handleUpgrade}
                    disabled={isLoading}
                    className="btn-primary text-lg px-12 py-4 w-full md:w-auto"
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
                    🔒 Secure payment via Stripe • 💳 All major cards accepted
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Testimonials */}
          <div className="grid md:grid-cols-2 gap-6 mb-12">
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="flex items-start gap-1 mb-3">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <p className="text-gray-700 italic mb-3">
                "AutoHVAC cut my Manual J calculation time from 2 hours to 10 minutes. 
                The accuracy is spot-on and my customers love the professional reports."
              </p>
              <p className="text-sm font-semibold text-gray-900">
                — Mike S., HVAC Contractor
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="flex items-start gap-1 mb-3">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <p className="text-gray-700 italic mb-3">
                "As a mechanical engineer, I appreciate the ACCA compliance and detailed 
                calculations. This tool pays for itself with just one project."
              </p>
              <p className="text-sm font-semibold text-gray-900">
                — Sarah L., PE
              </p>
            </div>
          </div>

          {/* FAQs */}
          <div className="bg-white rounded-xl p-8 shadow-sm">
            <h3 className="text-xl font-bold text-gray-900 mb-6">Frequently Asked Questions</h3>
            
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Can I cancel anytime?</h4>
                <p className="text-gray-700">
                  Yes! Cancel your subscription anytime from your dashboard. No questions asked, no hidden fees.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2">How accurate are the calculations?</h4>
                <p className="text-gray-700">
                  Our calculations follow ACCA Manual J standards and use ASHRAE climate data. 
                  Results are comparable to industry-standard software costing 10x more.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Do I need to install anything?</h4>
                <p className="text-gray-700">
                  No! AutoHVAC is 100% web-based. Upload your blueprint and get results in minutes from any device.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2">What file types are supported?</h4>
                <p className="text-gray-700">
                  We support PDF, PNG, JPG, and JPEG files up to 50MB. Most architectural blueprints work perfectly.
                </p>
              </div>
            </div>
          </div>

          {/* Bottom CTA */}
          <div className="text-center mt-12">
            <p className="text-gray-600 mb-6">
              Join thousands of professionals saving time on every project
            </p>
            <button
              onClick={handleUpgrade}
              disabled={isLoading}
              className="btn-primary text-lg px-12 py-4"
            >
              Start Your Pro Subscription
            </button>
            
            <div className="mt-8">
              <button
                onClick={() => router.push('/dashboard')}
                className="text-brand-600 hover:text-brand-700 text-sm font-medium"
              >
                ← Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}