import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import useSWR from 'swr'
import Head from 'next/head'
import { apiHelpers } from '@/lib/fetcher'
import ProjectCard from '../components/ProjectCard'
import MultiStepUpload from '../components/MultiStepUpload'
import Cookies from 'js-cookie'

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
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [filter, setFilter] = useState<string>('all')

  // Get email from URL params or cookies
  useEffect(() => {
    const emailFromQuery = router.query.email as string
    const emailFromCookie = Cookies.get('user_email')
    
    if (emailFromQuery) {
      setUserEmail(emailFromQuery)
      Cookies.set('user_email', emailFromQuery, { expires: 30 }) // 30 days
    } else if (emailFromCookie) {
      setUserEmail(emailFromCookie)
    } else {
      // Redirect to home if no email
      router.push('/')
    }
  }, [router])

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

  const handleLogout = () => {
    Cookies.remove('user_email')
    router.push('/')
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

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <nav className="bg-white shadow-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <div className="text-2xl font-bold text-brand-700">
                  AutoHVAC
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600">
                  {userEmail}
                </span>
                <button 
                  onClick={() => setIsUploadModalOpen(true)}
                  className="btn-primary"
                >
                  New Analysis
                </button>
                <button 
                  onClick={handleLogout}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header Section */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Your HVAC Projects
            </h1>
            <p className="text-gray-600">
              Manage and track your blueprint analyses
            </p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-2 bg-brand-100 rounded-lg">
                  <svg className="w-6 h-6 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Projects</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Completed</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.completed}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Processing</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.processing}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="p-2 bg-red-100 rounded-lg">
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Failed</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.failed}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <h2 className="text-lg font-semibold text-gray-900">Projects</h2>
                <div className="flex items-center space-x-2">
                  {[
                    { key: 'all', label: 'All' },
                    { key: 'completed', label: 'Completed' },
                    { key: 'processing', label: 'Processing' },
                    { key: 'pending', label: 'Pending' },
                    { key: 'failed', label: 'Failed' }
                  ].map(({ key, label }) => (
                    <button
                      key={key}
                      onClick={() => setFilter(key)}
                      className={`px-3 py-1 text-sm rounded-full transition-colors ${
                        filter === key
                          ? 'bg-brand-100 text-brand-700'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <button 
                onClick={() => mutate()}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Refresh"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          {/* Projects Grid */}
          {!data ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2 mb-4"></div>
                  <div className="space-y-2">
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="text-center py-12">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {filter === 'all' ? 'No projects yet' : `No ${filter} projects`}
              </h3>
              <p className="text-gray-600 mb-6">
                {filter === 'all' 
                  ? 'Get started by uploading your first blueprint for HVAC analysis.'
                  : `You don't have any ${filter} projects at the moment.`
                }
              </p>
              {filter === 'all' && (
                <button 
                  onClick={() => setIsUploadModalOpen(true)}
                  className="btn-primary"
                >
                  Upload Blueprint
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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