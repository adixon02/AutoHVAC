import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import useSWR from 'swr'
import Head from 'next/head'
import { apiHelpers } from '../lib/fetcher'
import ProjectCard from '../components/ProjectCard'
import MultiStepUpload from '../components/MultiStepUpload'
import Cookies from 'js-cookie'
import { useSession, signOut } from 'next-auth/react'

interface Project {
  id: string
  project_label: string
  filename: string
  status: string
  created_at: string
  completed_at?: string
  has_pdf_report: boolean
}

interface DashboardData {
  projects: Project[]
  total_count: number
}

export default function Dashboard() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [filter, setFilter] = useState<string>('all')
  const [showUserMenu, setShowUserMenu] = useState(false)

  // Get email from session
  useEffect(() => {
    if (session?.user?.email) {
      setUserEmail(session.user.email)
    } else if (status === 'unauthenticated') {
      // Middleware will handle the redirect
      router.push('/auth/signin?callbackUrl=/dashboard')
    }
  }, [session, status, router])
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showUserMenu && !(event.target as HTMLElement).closest('.user-menu-container')) {
        setShowUserMenu(false)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showUserMenu])

  // Fetch user projects
  const { data, error, mutate } = useSWR<DashboardData>(
    userEmail ? `projects-${userEmail}` : null,
    () => apiHelpers.getUserProjects(userEmail!, 50),
    {
      refreshInterval: 5000, // Refresh every 5 seconds for real-time updates
      revalidateOnFocus: true,
      errorRetryCount: 3
    }
  )

  const handleLogout = async () => {
    await signOut({ callbackUrl: '/' })
  }

  const filteredProjects = data?.projects?.filter(project => {
    if (filter === 'all') return true
    return project.status === filter
  }) || []

  const getProjectStats = () => {
    if (!data?.projects) return { total: 0, completed: 0, processing: 0, failed: 0 }
    
    return data.projects.reduce((stats, project) => {
      stats.total++
      switch (project.status) {
        case 'completed':
          stats.completed++
          break
        case 'processing':
        case 'pending':
          stats.processing++
          break
        case 'failed':
          stats.failed++
          break
      }
      return stats
    }, { total: 0, completed: 0, processing: 0, failed: 0 })
  }

  const stats = getProjectStats()

  // Check if user can upload new reports
  const { data: uploadEligibility } = useSWR(
    userEmail ? `can-upload-${userEmail}` : null,
    () => apiHelpers.checkCanUpload(userEmail!),
    { refreshInterval: 30000 } // Check every 30 seconds
  )

  const handleNewAnalysis = () => {
    if (uploadEligibility?.can_upload) {
      setIsUploadModalOpen(true)
    } else {
      // Redirect to full page upgrade experience
      router.push('/upgrade')
    }
  }

  if (!userEmail) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Dashboard Error</h1>
          <p className="text-gray-600 mb-6">
            Unable to load your projects. Please check your connection and try again.
          </p>
          <div className="space-x-4">
            <button 
              onClick={() => mutate()}
              className="btn-primary"
            >
              Retry
            </button>
            <button 
              onClick={() => router.push('/')}
              className="btn-secondary"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>Dashboard - AutoHVAC</title>
        <meta name="description" content="Your HVAC project dashboard" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25">
        {/* Header */}
        <nav className="bg-white/70 backdrop-blur-xl shadow-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <div className="flex items-center space-x-2 group cursor-pointer" onClick={() => router.push('/')}>
                  <div className="w-8 h-8 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center shadow-sm group-hover:shadow-md transition-all duration-200">
                    <span className="text-white font-bold text-sm">AH</span>
                  </div>
                  <span className="text-xl font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                    AutoHVAC
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                {/* Subscription Badge */}
                {uploadEligibility?.has_subscription && (
                  <span className="px-3 py-1 bg-gradient-to-r from-brand-600 to-brand-700 text-white text-xs font-semibold rounded-full shadow-sm">
                    PRO
                  </span>
                )}
                
                <button 
                  onClick={handleNewAnalysis}
                  className="btn-primary group"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                  </svg>
                  New Analysis
                </button>
                
                {/* User Menu Dropdown */}
                <div className="relative user-menu-container">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-all"
                  >
                    <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-600 rounded-full flex items-center justify-center text-white text-xs font-medium shadow-sm">
                      {userEmail?.charAt(0).toUpperCase()}
                    </div>
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-1 z-50 animate-scale-in">
                      <div className="px-4 py-2 border-b">
                        <p className="text-sm font-medium text-gray-900">{session?.user?.name || 'User'}</p>
                        <p className="text-xs text-gray-500">{userEmail}</p>
                      </div>
                      
                      <a
                        href="/account"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <div className="flex items-center">
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                          Account Settings
                        </div>
                      </a>
                      
                      <a
                        href="/billing"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <div className="flex items-center">
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                          </svg>
                          Billing & Subscription
                        </div>
                      </a>
                      
                      <div className="border-t my-1"></div>
                      
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <div className="flex items-center">
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                          </svg>
                          Sign Out
                        </div>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header Section */}
          <div className="mb-8">
            <h1 className="display-sm text-gray-900 mb-2">
              Your HVAC Projects
            </h1>
            <p className="text-lg text-gray-600">
              Manage and track your blueprint analyses
            </p>
          </div>

          {/* MVP Session Warning - removed as sessions now persist properly */}

          {/* Usage Indicator */}
          {uploadEligibility && (
            <div className={`mb-8 rounded-xl glass border ${
              uploadEligibility.can_upload 
                ? 'border-success-200 bg-success-50/50' 
                : 'border-warning-200 bg-warning-50/50'
            }`}>
              <div className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      uploadEligibility.can_upload ? 'bg-success-100' : 'bg-warning-100'
                    }`}>
                      <svg className={`w-5 h-5 ${
                        uploadEligibility.can_upload ? 'text-success-600' : 'text-warning-600'
                      }`} fill="currentColor" viewBox="0 0 24 24">
                        {uploadEligibility.can_upload ? (
                          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        ) : (
                          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        )}
                      </svg>
                    </div>
                    <div>
                      {uploadEligibility.can_upload ? (
                        <>
                          <h3 className="font-semibold text-gray-900">
                            {uploadEligibility.has_subscription ? 'Pro Subscription Active' : 'Free Upload Available'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-0.5">
                            {uploadEligibility.has_subscription 
                              ? 'You have unlimited blueprint analyses'
                              : 'You have 1 free blueprint analysis available'}
                          </p>
                        </>
                      ) : (
                        <>
                          <h3 className="font-semibold text-gray-900">Free Upload Used</h3>
                          <p className="text-sm text-gray-600 mt-0.5">
                            Upgrade to Pro for unlimited blueprint analyses
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                  {!uploadEligibility.has_subscription && !uploadEligibility.can_upload && (
                    <button
                      onClick={() => router.push('/upgrade')}
                      className="btn-primary btn-sm"
                    >
                      Upgrade to Pro
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="card hover:shadow-md transition-all duration-200">
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Total Projects</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-brand-50 to-brand-100 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <div className="card hover:shadow-md transition-all duration-200">
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Completed</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.completed}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-success-50 to-success-100 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <div className="card hover:shadow-md transition-all duration-200">
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Processing</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.processing}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <div className="card hover:shadow-md transition-all duration-200">
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Failed</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.failed}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-error-50 to-error-100 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-error-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1 p-1 bg-white rounded-lg shadow-sm border border-gray-200">
                {[
                  { key: 'all', label: 'All', count: stats.total },
                  { key: 'completed', label: 'Completed', count: stats.completed },
                  { key: 'processing', label: 'Processing', count: stats.processing },
                  { key: 'failed', label: 'Failed', count: stats.failed }
                ].map(({ key, label, count }) => (
                  <button
                    key={key}
                    onClick={() => setFilter(key)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                      filter === key
                        ? 'bg-gray-900 text-white shadow-sm'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    {label}
                    {count > 0 && (
                      <span className={`ml-2 px-1.5 py-0.5 text-xs rounded-full ${
                        filter === key
                          ? 'bg-white/20 text-white'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
              <button 
                onClick={() => mutate()}
                className="btn-icon hover:bg-gray-100 transition-all"
                title="Refresh"
              >
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          {/* Projects Grid */}
          {!data ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="card p-6 animate-pulse">
                  <div className="h-5 bg-gray-200 rounded-md w-3/4 mb-3"></div>
                  <div className="h-4 bg-gray-100 rounded w-1/2 mb-4"></div>
                  <div className="space-y-2">
                    <div className="h-3 bg-gray-100 rounded"></div>
                    <div className="h-3 bg-gray-100 rounded w-5/6"></div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="h-10 bg-gray-100 rounded-lg"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="card py-16">
              <div className="text-center">
                <div className="w-20 h-20 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {filter === 'all' ? 'No projects yet' : `No ${filter} projects`}
                </h3>
                <p className="text-gray-500 mb-6 max-w-sm mx-auto">
                  {filter === 'all' 
                    ? 'Get started by uploading your first blueprint for HVAC analysis.'
                    : `You don't have any ${filter} projects at the moment.`
                  }
                </p>
                {filter === 'all' && (
                  <button 
                    onClick={handleNewAnalysis}
                    className="btn-primary"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Upload Blueprint
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  userEmail={userEmail}
                  onDownload={() => {
                    console.log('Downloaded project:', project.id)
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      <MultiStepUpload 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
      />
    </>
  )
}