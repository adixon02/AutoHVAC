import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useSession } from 'next-auth/react'
import Head from 'next/head'
import Link from 'next/link'
import axios from 'axios'
import useSWR from 'swr'

export default function Billing() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  
  // Redirect if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin?callbackUrl=/billing')
    }
  }, [status, router])
  
  // Fetch subscription status
  const { data: subscription, mutate: mutateSubscription } = useSWR(
    session?.user?.id ? `/api/subscription/status` : null,
    () => axios.get('/api/subscription/status').then(res => res.data),
    { refreshInterval: 5000 }
  )
  
  // Fetch usage stats
  const { data: usageStats } = useSWR(
    session?.user?.email ? `/api/user/usage` : null,
    () => axios.get('/api/user/usage').then(res => res.data).catch(() => ({
      projectsThisMonth: 0,
      totalProjects: 0,
      lastProjectDate: null
    }))
  )
  
  const handleBillingPortal = async () => {
    setLoading(true)
    setMessage('')
    
    try {
      const response = await axios.post('/api/stripe/billing-portal', {
        returnUrl: window.location.href
      })
      
      if (response.data.portalUrl) {
        window.location.href = response.data.portalUrl
      }
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to open billing portal')
    } finally {
      setLoading(false)
    }
  }
  
  const handleUpgrade = async () => {
    setLoading(true)
    setMessage('')
    
    try {
      const response = await axios.post('/api/stripe/checkout', {
        successUrl: `${window.location.origin}/payment/success`,
        cancelUrl: window.location.href
      })
      
      if (response.data.checkoutUrl) {
        window.location.href = response.data.checkoutUrl
      }
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to start upgrade process')
    } finally {
      setLoading(false)
    }
  }
  
  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will lose access to Pro features at the end of your billing period.')) {
      return
    }
    
    setLoading(true)
    setMessage('')
    
    try {
      // Open billing portal for cancellation
      await handleBillingPortal()
    } catch (error) {
      setMessage('Failed to cancel subscription. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }
  
  return (
    <>
      <Head>
        <title>Billing & Subscription - AutoHVAC</title>
      </Head>
      
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <nav className="bg-white shadow-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-8">
                <Link href="/dashboard" className="text-2xl font-bold text-indigo-600">
                  AutoHVAC
                </Link>
                <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
                  ← Back to Dashboard
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600">{session?.user?.email}</span>
              </div>
            </div>
          </div>
        </nav>
        
        <div className="max-w-4xl mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Billing & Subscription</h1>
          
          {message && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800">{message}</p>
            </div>
          )}
          
          <div className="grid gap-6">
            {/* Current Plan Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Plan</h2>
              
              {subscription?.hasActiveSubscription ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200">
                    <div>
                      <h3 className="font-semibold text-indigo-900">AutoHVAC Pro</h3>
                      <p className="text-sm text-indigo-700">Unlimited blueprint analyses</p>
                      <p className="text-2xl font-bold text-indigo-900 mt-2">$97<span className="text-base font-normal">/month</span></p>
                    </div>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                      Active
                    </span>
                  </div>
                  
                  {subscription.details && (
                    <div className="grid grid-cols-2 gap-4 pt-4">
                      <div className="space-y-1">
                        <p className="text-sm text-gray-500">Status</p>
                        <p className="font-medium capitalize">{subscription.details.status}</p>
                      </div>
                      
                      {subscription.details.currentPeriodEnd && (
                        <div className="space-y-1">
                          <p className="text-sm text-gray-500">Next billing date</p>
                          <p className="font-medium">
                            {new Date(subscription.details.currentPeriodEnd).toLocaleDateString('en-US', {
                              month: 'long',
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </p>
                        </div>
                      )}
                      
                      {subscription.details.stripeDetails?.nextInvoiceAmount && (
                        <div className="space-y-1">
                          <p className="text-sm text-gray-500">Next payment</p>
                          <p className="font-medium">${subscription.details.stripeDetails.nextInvoiceAmount}</p>
                        </div>
                      )}
                      
                      {subscription.details.stripeDetails?.trialEnd && (
                        <div className="space-y-1">
                          <p className="text-sm text-gray-500">Trial ends</p>
                          <p className="font-medium">
                            {new Date(subscription.details.stripeDetails.trialEnd).toLocaleDateString()}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {subscription.details?.cancelAtPeriodEnd && (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-yellow-800 text-sm">
                        ⚠️ Your subscription will cancel on{' '}
                        {new Date(subscription.details.currentPeriodEnd).toLocaleDateString()}.
                        You'll retain access until then.
                      </p>
                    </div>
                  )}
                  
                  <div className="flex space-x-3 pt-4">
                    <button
                      onClick={handleBillingPortal}
                      disabled={loading}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      {loading ? 'Loading...' : 'Manage Billing'}
                    </button>
                    
                    {!subscription.details?.cancelAtPeriodEnd && (
                      <button
                        onClick={handleCancelSubscription}
                        disabled={loading}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
                      >
                        Cancel Subscription
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <h3 className="font-semibold text-gray-900">Free Plan</h3>
                      <p className="text-sm text-gray-600">
                        {session?.user?.freeReportUsed 
                          ? 'Your free report has been used' 
                          : '1 free blueprint analysis available'}
                      </p>
                    </div>
                    <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
                      Free
                    </span>
                  </div>
                  
                  <div className="p-6 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200">
                    <h3 className="font-semibold text-indigo-900 mb-3">Upgrade to Pro</h3>
                    <ul className="space-y-2 mb-4">
                      {[
                        'Unlimited HVAC load calculations',
                        'Professional PDF reports',
                        'Priority processing',
                        'Equipment recommendations',
                        'Cancel anytime'
                      ].map((benefit, idx) => (
                        <li key={idx} className="flex items-center text-sm text-indigo-700">
                          <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          {benefit}
                        </li>
                      ))}
                    </ul>
                    <button
                      onClick={handleUpgrade}
                      disabled={loading}
                      className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      {loading ? 'Loading...' : 'Upgrade to Pro - $97/month'}
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            {/* Usage Statistics */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Usage Statistics</h2>
              
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-gray-900">
                    {usageStats?.projectsThisMonth || 0}
                  </p>
                  <p className="text-sm text-gray-600">This Month</p>
                </div>
                
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-gray-900">
                    {usageStats?.totalProjects || 0}
                  </p>
                  <p className="text-sm text-gray-600">Total Projects</p>
                </div>
                
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-gray-900">
                    {subscription?.hasActiveSubscription ? '∞' : session?.user?.freeReportUsed ? '0' : '1'}
                  </p>
                  <p className="text-sm text-gray-600">Remaining</p>
                </div>
              </div>
              
              {usageStats?.lastProjectDate && (
                <p className="text-sm text-gray-500 mt-4">
                  Last project: {new Date(usageStats.lastProjectDate).toLocaleDateString()}
                </p>
              )}
            </div>
            
            {/* Billing Actions */}
            {subscription?.hasActiveSubscription && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Billing Actions</h2>
                
                <div className="space-y-3">
                  <button
                    onClick={handleBillingPortal}
                    className="w-full text-left p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">Update Payment Method</h3>
                        <p className="text-sm text-gray-500">Change your credit card or billing information</p>
                      </div>
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                  
                  <button
                    onClick={handleBillingPortal}
                    className="w-full text-left p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">Download Invoices</h3>
                        <p className="text-sm text-gray-500">Access your billing history and receipts</p>
                      </div>
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                  
                  {!subscription.details?.cancelAtPeriodEnd && (
                    <button
                      onClick={handleCancelSubscription}
                      className="w-full text-left p-4 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-medium text-red-900">Cancel Subscription</h3>
                          <p className="text-sm text-red-700">Cancel at the end of your billing period</p>
                        </div>
                        <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </button>
                  )}
                </div>
              </div>
            )}
            
            {/* Help Section */}
            <div className="bg-blue-50 rounded-lg p-6">
              <h3 className="font-semibold text-blue-900 mb-2">Need Help?</h3>
              <p className="text-blue-700 text-sm mb-3">
                If you have any questions about billing or need assistance with your subscription, we're here to help.
              </p>
              <a 
                href="mailto:support@autohvac.ai?subject=Billing%20Question"
                className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium text-sm"
              >
                Contact Support
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}