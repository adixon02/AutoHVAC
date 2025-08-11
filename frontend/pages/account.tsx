import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useSession, signOut } from 'next-auth/react'
import Head from 'next/head'
import Link from 'next/link'
import axios from 'axios'
import useSWR from 'swr'

export default function Account() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'subscription'>('profile')
  
  // Profile form
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileMessage, setProfileMessage] = useState('')
  
  // Password form
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState('')
  
  // Redirect if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin?callbackUrl=/account')
    }
  }, [status, router])
  
  // Load user data
  useEffect(() => {
    if (session?.user) {
      setName(session.user.name || '')
      setEmail(session.user.email || '')
    }
  }, [session])
  
  // Fetch subscription status
  const { data: subscription } = useSWR(
    session?.user ? `/api/subscription/status` : null,
    () => axios.get('/api/subscription/status').then(res => res.data)
  )
  
  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileLoading(true)
    setProfileMessage('')
    
    try {
      await axios.put('/api/user/profile', { name })
      setProfileMessage('Profile updated successfully!')
      setTimeout(() => setProfileMessage(''), 3000)
    } catch (error) {
      setProfileMessage('Failed to update profile')
    } finally {
      setProfileLoading(false)
    }
  }
  
  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordMessage('')
    
    if (newPassword !== confirmPassword) {
      setPasswordMessage('Passwords do not match')
      return
    }
    
    if (newPassword.length < 8) {
      setPasswordMessage('Password must be at least 8 characters')
      return
    }
    
    setPasswordLoading(true)
    
    try {
      await axios.post('/api/auth/change-password', {
        currentPassword,
        newPassword
      })
      setPasswordMessage('Password changed successfully!')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPasswordMessage(''), 3000)
    } catch (error: any) {
      setPasswordMessage(error.response?.data?.error || 'Failed to change password')
    } finally {
      setPasswordLoading(false)
    }
  }
  
  const handleBillingPortal = async () => {
    try {
      const response = await axios.post('/api/stripe/billing-portal', {
        returnUrl: window.location.href
      })
      if (response.data.portalUrl) {
        window.location.href = response.data.portalUrl
      }
    } catch (error) {
      console.error('Failed to open billing portal:', error)
    }
  }
  
  const handleUpgrade = () => {
    router.push('/upgrade')
  }
  
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-brand-200 border-t-brand-600"></div>
      </div>
    )
  }
  
  return (
    <>
      <Head>
        <title>Account Settings - AutoHVAC</title>
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25">
        {/* Header */}
        <nav className="bg-white/70 backdrop-blur-xl shadow-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-8">
                <Link href="/dashboard" className="flex items-center space-x-2 group">
                  <div className="w-8 h-8 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center shadow-sm group-hover:shadow-md transition-all duration-200">
                    <span className="text-white font-bold text-sm">AH</span>
                  </div>
                  <span className="text-xl font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                    AutoHVAC
                  </span>
                </Link>
                <Link href="/dashboard" className="text-gray-600 hover:text-gray-900 transition-colors">
                  ← Back to Dashboard
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                {/* User Menu Dropdown */}
                <div className="relative">
                  <div className="flex items-center space-x-2 px-3 py-2 rounded-lg">
                    <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-600 rounded-full flex items-center justify-center text-white text-xs font-medium shadow-sm">
                      {session?.user?.email?.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-sm text-gray-600">{session?.user?.email}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </nav>
        
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="mb-8">
            <h1 className="display-md text-gray-900">Account Settings</h1>
            <p className="text-gray-600 mt-2">Manage your account preferences and subscription</p>
          </div>
          
          {/* Tabs */}
          <div className="mb-8">
            <div className="flex space-x-2">
              {[
                { key: 'profile', label: 'Profile' },
                { key: 'password', label: 'Password' },
                { key: 'subscription', label: 'Subscription' }
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key as 'profile' | 'password' | 'subscription')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    activeTab === key
                      ? 'bg-gray-900 text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="card p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Profile Information</h2>
              <form onSubmit={handleProfileUpdate} className="space-y-6">
                <div>
                  <label htmlFor="name" className="label">
                    Name
                  </label>
                  <input
                    type="text"
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input"
                    placeholder="Enter your full name"
                  />
                </div>
                
                <div>
                  <label htmlFor="email" className="label">
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    disabled
                    className="input bg-gray-50 cursor-not-allowed"
                  />
                  <p className="helper-text">Email cannot be changed</p>
                </div>
                
                {profileMessage && (
                  <div className={`p-4 rounded-lg border ${
                    profileMessage.includes('success') 
                      ? 'bg-green-50 border-green-200 text-green-800' 
                      : 'bg-red-50 border-red-200 text-red-800'
                  }`}>
                    <div className="flex items-center">
                      <svg className={`w-5 h-5 mr-2 ${
                        profileMessage.includes('success') ? 'text-green-600' : 'text-red-600'
                      }`} fill="currentColor" viewBox="0 0 20 20">
                        {profileMessage.includes('success') ? (
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        ) : (
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        )}
                      </svg>
                      {profileMessage}
                    </div>
                  </div>
                )}
                
                <button
                  type="submit"
                  disabled={profileLoading}
                  className="btn-primary disabled:opacity-50"
                >
                  {profileLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                      Saving...
                    </>
                  ) : (
                    'Save Changes'
                  )}
                </button>
              </form>
            </div>
          )}
          
          {/* Password Tab */}
          {activeTab === 'password' && (
            <div className="card p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Change Password</h2>
              <form onSubmit={handlePasswordChange} className="space-y-6 max-w-md">
                <div>
                  <label htmlFor="currentPassword" className="label">
                    Current Password
                  </label>
                  <input
                    type="password"
                    id="currentPassword"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                    className="input"
                    placeholder="Enter your current password"
                  />
                </div>
                
                <div>
                  <label htmlFor="newPassword" className="label">
                    New Password
                  </label>
                  <input
                    type="password"
                    id="newPassword"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    className="input"
                    placeholder="Enter your new password"
                  />
                </div>
                
                <div>
                  <label htmlFor="confirmPassword" className="label">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    id="confirmPassword"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="input"
                    placeholder="Confirm your new password"
                  />
                </div>
                
                {passwordMessage && (
                  <div className={`p-4 rounded-lg border ${
                    passwordMessage.includes('success') 
                      ? 'bg-green-50 border-green-200 text-green-800' 
                      : 'bg-red-50 border-red-200 text-red-800'
                  }`}>
                    <div className="flex items-center">
                      <svg className={`w-5 h-5 mr-2 ${
                        passwordMessage.includes('success') ? 'text-green-600' : 'text-red-600'
                      }`} fill="currentColor" viewBox="0 0 20 20">
                        {passwordMessage.includes('success') ? (
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        ) : (
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        )}
                      </svg>
                      {passwordMessage}
                    </div>
                  </div>
                )}
                
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="btn-primary disabled:opacity-50"
                >
                  {passwordLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                      Changing...
                    </>
                  ) : (
                    'Change Password'
                  )}
                </button>
              </form>
            </div>
          )}
          
          {/* Subscription Tab */}
          {activeTab === 'subscription' && (
            <div className="space-y-6">
              {/* Current Plan */}
              <div className="card p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Current Plan</h2>
                
                {subscription?.hasActiveSubscription ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-200">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center mr-3">
                          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </div>
                        <div>
                          <h3 className="font-semibold text-green-900">AutoHVAC Pro</h3>
                          <p className="text-sm text-green-700">Unlimited blueprint analyses</p>
                        </div>
                      </div>
                      <span className="badge badge-success">
                        Active
                      </span>
                    </div>
                    
                    {subscription.details && (
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Status:</span>
                          <span className="font-medium capitalize">{subscription.details.status}</span>
                        </div>
                        {subscription.details.currentPeriodEnd && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">Next billing date:</span>
                            <span className="font-medium">
                              {new Date(subscription.details.currentPeriodEnd).toLocaleDateString()}
                            </span>
                          </div>
                        )}
                        {subscription.details.cancelAtPeriodEnd && (
                          <div className="p-3 bg-yellow-50 rounded-md">
                            <p className="text-yellow-800 text-sm">
                              Your subscription will cancel at the end of the current billing period
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className="pt-4 border-t border-gray-100">
                      <button
                        onClick={handleBillingPortal}
                        className="btn-primary"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Manage Subscription
                      </button>
                      <p className="helper-text mt-2">
                        Update payment method, download invoices, or cancel subscription
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-gray-75 rounded-xl border border-gray-200">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-r from-gray-400 to-gray-500 rounded-xl flex items-center justify-center mr-3">
                          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">Free Plan</h3>
                          <p className="text-sm text-gray-600">
                            {session?.user?.freeReportUsed 
                              ? 'Free report used' 
                              : '1 free blueprint analysis available'}
                          </p>
                        </div>
                      </div>
                      <span className="badge badge-gray">
                        Free
                      </span>
                    </div>
                    
                    <div className="pt-4 border-t border-gray-100">
                      <button
                        onClick={handleUpgrade}
                        className="btn-primary"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Upgrade to Pro
                      </button>
                      <p className="helper-text mt-2">
                        Get unlimited blueprint analyses for $97/month
                      </p>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Benefits */}
              <div className="card p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Pro Benefits</h2>
                <ul className="space-y-3">
                  {[
                    'Unlimited HVAC load calculations',
                    'Professional PDF reports',
                    'Priority processing',
                    'Advanced duct sizing tools',
                    'Equipment recommendations',
                    'Climate data for any US location',
                    'Email support',
                    'Cancel anytime'
                  ].map((benefit, idx) => (
                    <li key={idx} className="flex items-start">
                      <div className="flex-shrink-0 w-5 h-5 bg-green-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                        <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <span className="text-gray-700 text-sm">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}