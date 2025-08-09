import React from 'react'
import { downloadProjectReport } from '../lib/fetcher'

interface ProjectCardProps {
  project: {
    id: string
    project_label: string
    filename: string
    status: string
    created_at: string
    completed_at?: string
    has_pdf_report: boolean
  }
  userEmail: string
  onDownload?: (projectId: string) => void
}

const StatusBadge = ({ status }: { status: string }) => {
  const getStatusConfig = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          icon: '✓',
          label: 'Completed'
        }
      case 'processing':
        return {
          bg: 'bg-blue-100',
          text: 'text-blue-800',
          icon: '⟳',
          label: 'Processing'
        }
      case 'pending':
        return {
          bg: 'bg-yellow-100',
          text: 'text-yellow-800',
          icon: '⏳',
          label: 'Pending'
        }
      case 'failed':
        return {
          bg: 'bg-red-100',
          text: 'text-red-800',
          icon: '✗',
          label: 'Failed'
        }
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-800',
          icon: '?',
          label: status
        }
    }
  }

  const config = getStatusConfig(status)

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      <span className="mr-1">{config.icon}</span>
      {config.label}
    </span>
  )
}

export default function ProjectCard({ project, userEmail, onDownload }: ProjectCardProps) {
  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click when downloading
    try {
      await downloadProjectReport(project.id, userEmail)
      onDownload?.(project.id)
    } catch (error) {
      console.error('Download failed:', error)
      alert('Failed to download report. Please try again.')
    }
  }

  const handleCardClick = () => {
    // Open the analyzing page to view results/status
    window.open(`/analyzing/${project.id}`, '_blank')
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getProcessingTime = () => {
    if (!project.completed_at) return null
    
    const start = new Date(project.created_at)
    const end = new Date(project.completed_at)
    const diffMs = end.getTime() - start.getTime()
    const diffMins = Math.round(diffMs / 60000)
    
    if (diffMins < 1) return 'Less than 1 minute'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''}`
    
    const hours = Math.floor(diffMins / 60)
    const mins = diffMins % 60
    return `${hours}h ${mins}m`
  }

  return (
    <div 
      className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200 cursor-pointer"
      onClick={handleCardClick}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {project.project_label}
            </h3>
            <p className="text-sm text-gray-500 truncate">
              {project.filename}
            </p>
          </div>
          <div className="ml-4">
            <StatusBadge status={project.status} />
          </div>
        </div>

        {/* Project Details */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center text-sm text-gray-600">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a1 1 0 011-1h6a1 1 0 011 1v4h3a1 1 0 011 1v1H4V8a1 1 0 011-1h3z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 21v-8h8v8H8z" />
            </svg>
            Project ID: {project.id.substring(0, 8)}...
          </div>
          
          <div className="flex items-center text-sm text-gray-600">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Created: {formatDate(project.created_at)}
          </div>

          {project.completed_at && (
            <div className="flex items-center text-sm text-gray-600">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Completed in {getProcessingTime()}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3">
          {project.status === 'completed' && project.has_pdf_report ? (
            <button
              onClick={handleDownload}
              className="flex-1 btn-primary text-sm py-2"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download Report
            </button>
          ) : project.status === 'processing' || project.status === 'pending' ? (
            <div className="flex-1 text-center">
              <div className="inline-flex items-center text-sm text-blue-600">
                <svg className="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Processing...
              </div>
            </div>
          ) : project.status === 'failed' ? (
            <div className="flex-1 text-center">
              <span className="text-sm text-red-600">Analysis failed - Click to view details</span>
            </div>
          ) : null}

          {/* Info Icon */}
          <div 
            className="p-2 text-gray-400"
            onClick={(e) => e.stopPropagation()}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  )
}