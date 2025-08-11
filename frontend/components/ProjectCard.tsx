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
          bg: 'bg-success-50 border-success-200',
          text: 'text-success-700',
          dot: 'bg-success-500',
          label: 'Completed'
        }
      case 'processing':
        return {
          bg: 'bg-blue-50 border-blue-200',
          text: 'text-blue-700',
          dot: 'bg-blue-500',
          label: 'Processing'
        }
      case 'pending':
        return {
          bg: 'bg-warning-50 border-warning-200',
          text: 'text-warning-700',
          dot: 'bg-warning-500',
          label: 'Pending'
        }
      case 'failed':
        return {
          bg: 'bg-error-50 border-error-200',
          text: 'text-error-700',
          dot: 'bg-error-500',
          label: 'Failed'
        }
      default:
        return {
          bg: 'bg-gray-50 border-gray-200',
          text: 'text-gray-700',
          dot: 'bg-gray-500',
          label: status
        }
    }
  }

  const config = getStatusConfig(status)

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg} ${config.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${config.dot}`}></span>
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
      className="card hover:shadow-lg transition-all duration-300 cursor-pointer group"
      onClick={handleCardClick}
    >
      <div className="p-6 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate group-hover:text-brand-600 transition-colors">
              {project.project_label}
            </h3>
            <p className="text-sm text-gray-500 truncate mt-1">
              {project.filename}
            </p>
          </div>
          <div className="ml-4">
            <StatusBadge status={project.status} />
          </div>
        </div>

        {/* Project Details */}
        <div className="space-y-2.5 py-3 border-t border-gray-100">
          <div className="flex items-center text-sm text-gray-600">
            <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center mr-3">
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
              </svg>
            </div>
            <span className="text-gray-900 font-medium">ID:</span>
            <span className="ml-1 font-mono text-gray-500">{project.id.substring(0, 8)}...</span>
          </div>
          
          <div className="flex items-center text-sm text-gray-600">
            <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center mr-3">
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-gray-900 font-medium">Created:</span>
            <span className="ml-1 text-gray-500">{formatDate(project.created_at)}</span>
          </div>

          {project.completed_at && (
            <div className="flex items-center text-sm text-gray-600">
              <div className="w-8 h-8 rounded-lg bg-success-50 flex items-center justify-center mr-3">
                <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="text-gray-900 font-medium">Duration:</span>
              <span className="ml-1 text-gray-500">{getProcessingTime()}</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 pt-3 border-t border-gray-100">
          {project.status === 'completed' && project.has_pdf_report ? (
            <button
              onClick={handleDownload}
              className="flex-1 btn-primary btn-sm group/btn"
            >
              <svg className="w-4 h-4 mr-2 group-hover/btn:translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
              </svg>
              Download Report
            </button>
          ) : project.status === 'processing' || project.status === 'pending' ? (
            <div className="flex-1">
              <div className="flex items-center justify-center py-2 px-4 bg-blue-50 rounded-lg">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent mr-2"></div>
                <span className="text-sm font-medium text-blue-700">Processing...</span>
              </div>
            </div>
          ) : project.status === 'failed' ? (
            <div className="flex-1">
              <div className="bg-error-50 border border-error-200 rounded-lg px-4 py-2.5">
                <p className="text-sm text-error-700 font-medium">Analysis unsuccessful</p>
                <p className="text-xs text-error-600 mt-0.5">Click to view details</p>
              </div>
            </div>
          ) : null}

          {/* View Details Button */}
          <button 
            className="btn-icon hover:bg-gray-100 transition-all"
            onClick={(e) => e.stopPropagation()}
            title="View details"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}