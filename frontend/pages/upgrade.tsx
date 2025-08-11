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

      <div className="min-h-screen bg-white gradient-mesh noise relative overflow-hidden">
        {/* Premium Header */}
        <nav className="relative z-50">
          <div className="glass border-0 border-b border-white/10 backdrop-blur-xl">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="display-xs gradient-text cursor-pointer transition-all duration-300 hover:scale-105" onClick={() => router.push('/')}>
                  AutoHVAC
                </div>
                {userEmail && (
                  <div className="flex items-center gap-3">
                    <div className="avatar avatar-sm bg-brand-100 text-brand-700 font-medium">
                      {userEmail.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-sm text-gray-700 font-medium">{userEmail}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="relative z-10">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            {/* Premium Header */}
            <div className="text-center mb-16 animate-fade-in">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-full mb-6 animate-scale-in">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-green-700">First calculation complete</span>
              </div>
              <h1 className="display-lg gradient-text mb-6 text-balance animate-slide-up">
                Ready to unlock unlimited calculations?
              </h1>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed animate-slide-up" style={{animationDelay: '0.1s'}}>
                Great news - your first HVAC load calculation is complete. 
                Upgrade to Pro to continue analyzing blueprints and access premium features designed for professionals.
              </p>
            </div>

            {/* Premium Pricing Card */}
            <div className="relative mb-16 animate-slide-up" style={{animationDelay: '0.2s'}}>
              <div className="absolute inset-0 gradient-brand rounded-3xl blur-3xl opacity-20 scale-105"></div>
              <div className="relative card-glass rounded-3xl overflow-hidden border-2 border-white/20 backdrop-blur-2xl">
                {/* Premium Badge */}
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-10">
                  <div className="gradient-border-animated px-6 py-2 bg-white rounded-full">
                    <span className="gradient-text font-semibold text-sm">Most Popular</span>
                  </div>
                </div>
                
                <div className="p-12">
                  <div className="text-center mb-10">
                    <div className="inline-flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-2xl gradient-brand flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <div>
                        <h2 className="display-sm text-gray-900 font-bold">AutoHVAC Pro</h2>
                      </div>
                    </div>
                    <div className="flex items-baseline justify-center gap-3 mb-4">
                      <span className="display-lg text-gray-900 font-bold">$97</span>
                      <span className="text-xl text-gray-600 font-medium">/month</span>
                    </div>
                    <div className="flex items-center justify-center gap-6 text-sm text-gray-600">
                      <div className="flex items-center gap-1">
                        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span>Cancel anytime</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span>No setup fees</span>
                      </div>
                    </div>
                  </div>

                  {/* Premium Features Grid */}
                  <div className="grid md:grid-cols-2 gap-8 mb-10">
                    <div className="space-y-6">
                      <h3 className="display-xs text-gray-900 font-bold mb-6">Everything You Get:</h3>
                      <div className="space-y-4">
                        {[
                          { icon: '∞', text: 'Unlimited HVAC load calculations', highlight: true },
                          { icon: '⚡', text: 'Instant PDF report downloads' },
                          { icon: '🔧', text: 'Advanced duct sizing tools' },
                          { icon: '💡', text: 'Equipment recommendations' },
                          { icon: '🌡️', text: 'Climate data for any US location' },
                          { icon: '🚀', text: 'Priority email support' },
                          { icon: '✨', text: 'New features as we ship them' }
                        ].map((feature, idx) => (
                          <div key={idx} className={`flex items-start gap-4 p-3 rounded-xl transition-all duration-200 hover:bg-white/50 ${feature.highlight ? 'bg-brand-50/50 border border-brand-200/50' : ''}`}>
                            <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
                              {typeof feature.icon === 'string' ? (
                                <span className="text-sm">{feature.icon}</span>
                              ) : (
                                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                              )}
                            </div>
                            <span className="text-gray-800 font-medium leading-relaxed">{feature.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-6">
                      <h3 className="display-xs text-gray-900 font-bold mb-6">Perfect For:</h3>
                      <div className="space-y-4">
                        {[
                          { icon: '🔨', text: 'HVAC contractors & installers' },
                          { icon: '⚙️', text: 'Mechanical engineers' },
                          { icon: '🏗️', text: 'Building designers & architects' },
                          { icon: '📊', text: 'Energy consultants' },
                          { icon: '🏠', text: 'Home performance professionals' },
                          { icon: '📈', text: 'Anyone doing 3+ projects/month' }
                        ].map((useCase, idx) => (
                          <div key={idx} className="flex items-start gap-4 p-3 rounded-xl hover:bg-white/50 transition-all duration-200">
                            <div className="w-8 h-8 rounded-lg bg-brand-100 flex items-center justify-center flex-shrink-0">
                              <span className="text-sm">{useCase.icon}</span>
                            </div>
                            <span className="text-gray-800 font-medium leading-relaxed">{useCase.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Premium CTA Section */}
                  <div className="text-center space-y-6">
                    {error && (
                      <div className="alert alert-error rounded-xl backdrop-blur-sm animate-slide-down">
                        <div className="flex items-center gap-3">
                          <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <span className="font-medium">{error}</span>
                        </div>
                      </div>
                    )}
                    
                    {stripeUnavailable ? (
                      <div className="card-glass rounded-2xl p-8 border border-yellow-200/50 animate-slide-down">
                        <div className="w-16 h-16 rounded-2xl bg-yellow-100 flex items-center justify-center mx-auto mb-6">
                          <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                          </svg>
                        </div>
                        <h3 className="display-xs text-yellow-800 mb-4">
                          Payment System Temporarily Unavailable
                        </h3>
                        <p className="text-yellow-700 mb-8 leading-relaxed">
                          We're experiencing a temporary issue with our payment processor. 
                          Please try again in a few minutes, or contact our support team for assistance.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4">
                          <button
                            onClick={() => {
                              setStripeUnavailable(false)
                              setError(null)
                            }}
                            className="btn-secondary btn-lg flex-1"
                          >
                            Try Again
                          </button>
                          <a
                            href={`mailto:support@autohvac.com?subject=Upgrade%20Request&body=Hi,%20I'd%20like%20to%20upgrade%20to%20Pro.%20My%20email%20is:%20${userEmail || ''}`}
                            className="btn-primary btn-lg flex-1 no-underline"
                          >
                            Contact Support
                          </a>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-6">
                        <button
                          onClick={handleUpgrade}
                          disabled={isLoading}
                          className="btn-primary btn-xl px-16 py-5 text-lg font-semibold shadow-2xl hover:shadow-3xl transition-all duration-300 hover:scale-105 disabled:hover:scale-100 disabled:hover:shadow-2xl relative overflow-hidden group"
                        >
                          <div className="absolute inset-0 bg-gradient-to-r from-brand-600 to-brand-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                          <span className="relative z-10 flex items-center justify-center gap-3">
                            {isLoading ? (
                              <>
                                <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                <span>Processing...</span>
                              </>
                            ) : (
                              <>
                                <span>Upgrade to Pro</span>
                                <svg className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                </svg>
                              </>
                            )}
                          </span>
                        </button>

                        <div className="flex items-center justify-center gap-8 text-sm text-gray-600">
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                            </svg>
                            <span>Secure payment via Stripe</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4zM18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" />
                            </svg>
                            <span>All major cards accepted</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Premium Testimonials */}
            <div className="grid md:grid-cols-2 gap-8 mb-16 animate-slide-up" style={{animationDelay: '0.3s'}}>
              <div className="card-glass rounded-2xl p-8 hover:shadow-2xl transition-all duration-500 hover:scale-105 group">
                <div className="flex items-center gap-1 mb-6">
                  {[...Array(5)].map((_, i) => (
                    <svg key={i} className="w-6 h-6 text-yellow-400 transition-transform duration-200 group-hover:scale-110" fill="currentColor" viewBox="0 0 20 20" style={{animationDelay: `${i * 0.1}s`}}>
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <blockquote className="text-lg text-gray-800 font-medium mb-6 leading-relaxed">
                  "AutoHVAC cut my Manual J calculation time from 2 hours to 10 minutes. 
                  The accuracy is spot-on and my customers love the professional reports."
                </blockquote>
                <div className="flex items-center gap-4">
                  <div className="avatar avatar-md bg-gradient-to-br from-blue-500 to-blue-600 text-white font-bold">
                    M
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">Mike S.</div>
                    <div className="text-sm text-gray-600">HVAC Contractor</div>
                  </div>
                </div>
              </div>

              <div className="card-glass rounded-2xl p-8 hover:shadow-2xl transition-all duration-500 hover:scale-105 group">
                <div className="flex items-center gap-1 mb-6">
                  {[...Array(5)].map((_, i) => (
                    <svg key={i} className="w-6 h-6 text-yellow-400 transition-transform duration-200 group-hover:scale-110" fill="currentColor" viewBox="0 0 20 20" style={{animationDelay: `${i * 0.1}s`}}>
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <blockquote className="text-lg text-gray-800 font-medium mb-6 leading-relaxed">
                  "As a mechanical engineer, I appreciate the ACCA compliance and detailed 
                  calculations. This tool pays for itself with just one project."
                </blockquote>
                <div className="flex items-center gap-4">
                  <div className="avatar avatar-md bg-gradient-to-br from-green-500 to-green-600 text-white font-bold">
                    S
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">Sarah L.</div>
                    <div className="text-sm text-gray-600">Mechanical Engineer, PE</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Premium FAQs */}
            <div className="card-glass rounded-3xl p-10 mb-16 animate-slide-up" style={{animationDelay: '0.4s'}}>
              <div className="text-center mb-10">
                <h3 className="display-sm gradient-text mb-4">Frequently Asked Questions</h3>
                <p className="text-lg text-gray-600">Everything you need to know about AutoHVAC Pro</p>
              </div>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="space-y-8">
                  <div className="group">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 group-hover:bg-brand-200 transition-colors duration-200">
                        <svg className="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h4 className="text-xl font-bold text-gray-900 group-hover:text-brand-700 transition-colors duration-200">Can I cancel anytime?</h4>
                    </div>
                    <p className="text-gray-700 leading-relaxed ml-12">
                      Yes! Cancel your subscription anytime from your dashboard. No questions asked, no hidden fees, no hassle.
                    </p>
                  </div>

                  <div className="group">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 group-hover:bg-brand-200 transition-colors duration-200">
                        <svg className="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h4 className="text-xl font-bold text-gray-900 group-hover:text-brand-700 transition-colors duration-200">How accurate are the calculations?</h4>
                    </div>
                    <p className="text-gray-700 leading-relaxed ml-12">
                      Our calculations follow ACCA Manual J standards and use ASHRAE climate data. 
                      Results are comparable to industry-standard software costing 10x more.
                    </p>
                  </div>
                </div>

                <div className="space-y-8">
                  <div className="group">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 group-hover:bg-brand-200 transition-colors duration-200">
                        <svg className="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <h4 className="text-xl font-bold text-gray-900 group-hover:text-brand-700 transition-colors duration-200">Do I need to install anything?</h4>
                    </div>
                    <p className="text-gray-700 leading-relaxed ml-12">
                      No! AutoHVAC is 100% web-based. Upload your blueprint and get results in minutes from any device, anywhere.
                    </p>
                  </div>

                  <div className="group">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 group-hover:bg-brand-200 transition-colors duration-200">
                        <svg className="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <h4 className="text-xl font-bold text-gray-900 group-hover:text-brand-700 transition-colors duration-200">What file types are supported?</h4>
                    </div>
                    <p className="text-gray-700 leading-relaxed ml-12">
                      We support PDF, PNG, JPG, and JPEG files up to 50MB. Most architectural blueprints work perfectly out of the box.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Premium Bottom CTA */}
            <div className="text-center animate-slide-up" style={{animationDelay: '0.5s'}}>
              <div className="mb-12">
                <div className="inline-flex items-center gap-2 mb-4">
                  <div className="flex -space-x-2">
                    <div className="avatar avatar-sm bg-gradient-to-br from-blue-500 to-blue-600 text-white font-bold border-2 border-white">M</div>
                    <div className="avatar avatar-sm bg-gradient-to-br from-green-500 to-green-600 text-white font-bold border-2 border-white">S</div>
                    <div className="avatar avatar-sm bg-gradient-to-br from-purple-500 to-purple-600 text-white font-bold border-2 border-white">J</div>
                    <div className="avatar avatar-sm bg-gradient-to-br from-orange-500 to-orange-600 text-white font-bold border-2 border-white">+</div>
                  </div>
                </div>
                <p className="text-xl text-gray-600 font-medium mb-8">
                  Join thousands of professionals saving time on every project
                </p>
                {!stripeUnavailable && (
                  <button
                    onClick={handleUpgrade}
                    disabled={isLoading}
                    className="btn-primary btn-xl px-16 py-5 text-lg font-semibold shadow-2xl hover:shadow-3xl transition-all duration-300 hover:scale-105 disabled:hover:scale-100 disabled:hover:shadow-2xl mb-8 relative overflow-hidden group"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-brand-600 to-brand-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    <span className="relative z-10 flex items-center justify-center gap-3">
                      {isLoading ? (
                        <>
                          <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <span>Start Your Pro Subscription</span>
                          <svg className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                          </svg>
                        </>
                      )}
                    </span>
                  </button>
                )}
              </div>
              
              <div className="pt-8 border-t border-gray-200">
                <button
                  onClick={() => router.push('/dashboard')}
                  className="inline-flex items-center gap-2 text-brand-600 hover:text-brand-700 font-medium transition-all duration-200 hover:gap-3"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                  <span>Back to Dashboard</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}