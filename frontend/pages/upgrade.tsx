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

      <div className="min-h-screen bg-white">
        {/* Simple Header */}
        <nav className="border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-2 group cursor-pointer" onClick={() => router.push('/')}>
                <div className="w-8 h-8 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center shadow-sm group-hover:shadow-md transition-all duration-200">
                  <span className="text-white font-bold text-sm">AH</span>
                </div>
                <span className="text-xl font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                  AutoHVAC
                </span>
              </div>
              {userEmail && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-600">{userEmail}</span>
                  <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-gray-600 text-xs font-medium">
                    {userEmail.charAt(0).toUpperCase()}
                  </div>
                </div>
              )}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header Section */}
          <div className="text-center mb-12">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200 mb-4">
              Upgrade
            </span>
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Unlock unlimited calculations
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Simple, transparent pricing that grows with you. No hidden fees, cancel anytime.
            </p>
          </div>

          {/* Success Badge */}
          {userEmail && (
            <div className="flex justify-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-success-50 border border-success-200 rounded-full">
                <svg className="w-5 h-5 text-success-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium text-success-700">First calculation complete</span>
              </div>
            </div>
          )}

          {/* Pricing Card */}
          <div className="max-w-lg mx-auto mb-12">
            <div className="bg-white rounded-2xl border-2 border-gray-200 shadow-lg overflow-hidden">
              {/* Card Header */}
              <div className="bg-gray-50 px-8 py-6 border-b border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xl font-bold text-gray-900">Pro plan</h2>
                  <span className="px-3 py-1 bg-brand-100 text-brand-700 text-xs font-semibold rounded-full">
                    Popular
                  </span>
                </div>
                <p className="text-sm text-gray-600">Perfect for professionals and growing teams</p>
              </div>

              {/* Price Section */}
              <div className="px-8 py-8">
                <div className="flex items-baseline mb-8">
                  <span className="text-5xl font-bold text-gray-900">$97</span>
                  <span className="text-gray-600 ml-2">per month</span>
                </div>

                {/* Features Title */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">
                    Everything included
                  </h3>
                </div>

                {/* Features List */}
                <ul className="space-y-4 mb-8">
                  {[
                    'Unlimited HVAC load calculations',
                    'Instant PDF report downloads',
                    'Advanced duct sizing tools',
                    'Equipment recommendations',
                    'Climate data for any US location',
                    'Priority email support',
                    'New features as we ship them',
                    'Cancel anytime'
                  ].map((feature, idx) => (
                    <li key={idx} className="flex items-start">
                      <svg className="w-5 h-5 text-success-500 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <button
                  onClick={handleUpgrade}
                  disabled={isLoading}
                  className="w-full btn-primary btn-lg"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin h-5 w-5 mr-3" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing...
                    </span>
                  ) : (
                    'Get started'
                  )}
                </button>

                {/* Trust Badges */}
                <div className="flex items-center justify-center gap-6 mt-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                    </svg>
                    Secure payment
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Cancel anytime
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="max-w-lg mx-auto mb-8">
              <div className="bg-error-50 border border-error-200 rounded-lg p-4">
                <div className="flex">
                  <svg className="w-5 h-5 text-error-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div className="ml-3">
                    <p className="text-sm text-error-700">{error}</p>
                    {stripeUnavailable && (
                      <p className="text-sm text-error-600 mt-1">
                        Please try again later or contact support if the issue persists.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Use Cases Grid */}
          <div className="grid md:grid-cols-2 gap-8 mb-12">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Perfect for</h3>
              <ul className="space-y-3">
                {[
                  { icon: '🔨', text: 'HVAC contractors & installers' },
                  { icon: '⚙️', text: 'Mechanical engineers' },
                  { icon: '🏗️', text: 'Building designers & architects' },
                  { icon: '📊', text: 'Energy consultants' },
                  { icon: '🏠', text: 'Home performance professionals' },
                  { icon: '📈', text: 'Anyone doing 3+ projects/month' }
                ].map((item, idx) => (
                  <li key={idx} className="flex items-center text-gray-700">
                    <span className="mr-3 text-lg">{item.icon}</span>
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Key benefits</h3>
              <ul className="space-y-3">
                {[
                  { icon: '⚡', text: 'Save 95% of calculation time' },
                  { icon: '✅', text: '100% ACCA compliant' },
                  { icon: '📄', text: 'Professional PDF reports' },
                  { icon: '🎯', text: 'Accurate equipment sizing' },
                  { icon: '💰', text: 'Win more bids' },
                  { icon: '📧', text: 'Priority support' }
                ].map((item, idx) => (
                  <li key={idx} className="flex items-center text-gray-700">
                    <span className="mr-3 text-lg">{item.icon}</span>
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Testimonials */}
          <div className="bg-gray-50 rounded-2xl p-8 mb-12">
            <h2 className="text-xl font-bold text-gray-900 text-center mb-8">Trusted by professionals</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {[
                {
                  quote: "AutoHVAC has transformed our workflow. What used to take hours now takes minutes.",
                  author: "Mike Thompson",
                  role: "HVAC Contractor",
                  avatar: "MT"
                },
                {
                  quote: "The accuracy and detail in the reports are impressive. Worth every penny.",
                  author: "Sarah Chen",
                  role: "Mechanical Engineer",
                  avatar: "SC"
                }
              ].map((testimonial, idx) => (
                <div key={idx} className="bg-white rounded-xl p-6">
                  <p className="text-gray-700 mb-4 italic">"{testimonial.quote}"</p>
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 text-sm font-semibold mr-3">
                      {testimonial.avatar}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{testimonial.author}</p>
                      <p className="text-xs text-gray-600">{testimonial.role}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* FAQs */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 text-center mb-8">Frequently asked questions</h2>
            <div className="space-y-6">
              {[
                {
                  q: "Can I cancel anytime?",
                  a: "Yes! You can cancel your subscription at any time. You'll continue to have access until the end of your billing period."
                },
                {
                  q: "What payment methods do you accept?",
                  a: "We accept all major credit cards and debit cards through our secure payment processor, Stripe."
                },
                {
                  q: "Do you offer refunds?",
                  a: "We offer a 30-day money-back guarantee. If you're not satisfied, contact us for a full refund."
                },
                {
                  q: "How quickly can I get started?",
                  a: "Immediately! Once you upgrade, you can start uploading and analyzing blueprints right away."
                }
              ].map((faq, idx) => (
                <div key={idx} className="border-b border-gray-200 pb-6 last:border-0">
                  <h3 className="text-base font-semibold text-gray-900 mb-2">{faq.q}</h3>
                  <p className="text-gray-600">{faq.a}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="text-center pt-8 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-4">
              Questions? Email us at{' '}
              <a href="mailto:support@autohvac.ai" className="text-brand-600 hover:text-brand-700">
                support@autohvac.ai
              </a>
            </p>
            <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
              <a href="/terms" className="hover:text-gray-700">Terms of Service</a>
              <a href="/privacy" className="hover:text-gray-700">Privacy Policy</a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}