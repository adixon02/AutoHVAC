import React, { useState } from 'react'

interface ShareModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  projectName: string
}

export default function ShareModal({ isOpen, onClose, projectId, projectName }: ShareModalProps) {
  const [copied, setCopied] = useState(false)
  
  // Generate shareable URL
  const shareUrl = typeof window !== 'undefined' 
    ? `${window.location.origin}/analyzing/${projectId}`
    : ''

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleEmailShare = () => {
    const subject = encodeURIComponent(`HVAC Analysis: ${projectName}`)
    const body = encodeURIComponent(`Check out my HVAC load calculation report:\n\n${shareUrl}`)
    window.location.href = `mailto:?subject=${subject}&body=${body}`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-brand-700">
              Share Report
            </h3>
            <button
              onClick={onClose}
              className="btn-icon"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-gray-600 mb-6">
            Share this HVAC analysis report with contractors, team members, or clients.
          </p>

          {/* URL Copy Field */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Shareable Link
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={shareUrl}
                readOnly
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm text-gray-700"
              />
              <button
                onClick={handleCopyLink}
                className={`btn-small font-medium transition-all ${
                  copied 
                    ? 'bg-green-500 text-white hover:bg-green-600' 
                    : 'bg-brand-700 text-white hover:bg-brand-800'
                }`}
              >
                {copied ? (
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Copied!
                  </span>
                ) : (
                  'Copy'
                )}
              </button>
            </div>
          </div>

          {/* Share Options */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-700">Share via</h4>
            
            <button
              onClick={handleEmailShare}
              className="w-full flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span className="text-gray-700">Email</span>
            </button>

            {/* Note about access */}
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-xs text-blue-700">
                <strong>Note:</strong> Anyone with this link can view the report. The link remains active as long as the report exists.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}