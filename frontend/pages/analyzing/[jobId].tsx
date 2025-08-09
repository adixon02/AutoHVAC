import { useRouter } from 'next/router'
import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { apiHelpers } from '../../lib/fetcher'
import Head from 'next/head'
import ShareModal from '../../components/ShareModal'
import { useSession } from 'next-auth/react'
import Cookies from 'js-cookie'
import ResultsPreview from '../../components/ResultsPreview'

interface JobStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: any
  error?: string
}

interface ProcessingStage {
  title: string
  description: string
  status: 'completed' | 'active' | 'pending'
  stats: string
}

const hvacFacts = [
  {
    fact: "Manual J calculations consider your local climate, home orientation, insulation levels, and window placement to determine the exact heating and cooling needs for each room.",
    icon: "🏠"
  },
  {
    fact: "Proper HVAC sizing is crucial - oversized systems cycle on and off frequently, leading to poor humidity control and energy waste.",
    icon: "⚡"
  },
  {
    fact: "The ideal indoor temperature difference between rooms should be no more than 2-3°F for optimal comfort.",
    icon: "🌡️"
  },
  {
    fact: "Modern HVAC systems can be 95%+ efficient, meaning nearly all the energy consumed goes directly into heating or cooling your home.",
    icon: "🔧"
  },
  {
    fact: "Room orientation matters! South-facing rooms receive more solar heat gain and may need larger cooling capacity.",
    icon: "☀️"
  },
  {
    fact: "A properly designed duct system can improve efficiency by 20-40% compared to poorly designed systems.",
    icon: "🏭"
  },
  {
    fact: "Heat pumps can provide both heating and cooling, and are 2-3 times more efficient than traditional electric heating.",
    icon: "♻️"
  }
]

const technicalStatusMessages = [
  "📐 Extracting room dimensions from blueprint layers...",
  "🏠 Identifying HVAC zones and thermal boundaries...",
  "🌡️ Calculating heat transfer coefficients for each surface...",
  "🪟 Analyzing window placement and solar heat gain factors...",
  "📊 Computing sensible and latent cooling loads per zone...",
  "💨 Determining optimal airflow requirements (CFM) for each room...",
  "⚡ Calculating peak heating and cooling demands...",
  "🔧 Sizing equipment based on ACCA Manual S guidelines...",
  "📈 Optimizing system efficiency and comfort parameters...",
  "✅ Generating comprehensive load calculation report..."
]

function ProcessingStage({ title, description, status, stats }: ProcessingStage) {
  return (
    <div className={`p-4 rounded-lg border-l-4 transition-all duration-500 ${
      status === 'completed' ? 'bg-green-50 border-green-400' :
      status === 'active' ? 'bg-blue-50 border-blue-400' :
      'bg-gray-50 border-gray-300'
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className={`w-6 h-6 rounded-full mt-0.5 flex items-center justify-center ${
            status === 'completed' ? 'bg-green-500' :
            status === 'active' ? 'bg-blue-500 animate-pulse' :
            'bg-gray-300'
          }`}>
            {status === 'completed' ? (
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            ) : status === 'active' ? (
              <div className="w-2 h-2 bg-white rounded-full"></div>
            ) : (
              <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            )}
          </div>
          <div>
            <h4 className={`font-medium ${
              status === 'completed' ? 'text-green-800' :
              status === 'active' ? 'text-blue-800' :
              'text-gray-600'
            }`}>
              {title}
            </h4>
            <p className={`text-sm mt-1 ${
              status === 'completed' ? 'text-green-600' :
              status === 'active' ? 'text-blue-600' :
              'text-gray-500'
            }`}>
              {description}
            </p>
          </div>
        </div>
        <div className={`text-xs px-2 py-1 rounded ${
          status === 'completed' ? 'bg-green-100 text-green-700' :
          status === 'active' ? 'bg-blue-100 text-blue-700' :
          'bg-gray-100 text-gray-600'
        }`}>
          {stats}
        </div>
      </div>
    </div>
  )
}

function EducationalFact({ fact, icon }: { fact: string; icon: string }) {
  return (
    <div className="p-4 bg-gradient-to-r from-brand-50 to-blue-50 rounded-lg border border-brand-100">
      <div className="flex items-start space-x-3">
        <div className="text-2xl">{icon}</div>
        <div>
          <p className="text-sm text-brand-700 font-medium">Did you know?</p>
          <p className="text-sm text-brand-600 mt-1">{fact}</p>
        </div>
      </div>
    </div>
  )
}

// Helper functions for intelligent error handling
function getErrorMessage(error: string | undefined): string {
  if (!error) return "The analysis couldn't be completed due to an unexpected issue."
  
  const errorLower = error.toLowerCase()
  
  if (errorLower.includes('pdf') || errorLower.includes('file')) {
    return "There was an issue reading your blueprint file. The file might be corrupted or in an unsupported format."
  }
  if (errorLower.includes('timeout')) {
    return "The analysis took longer than expected. This usually happens with very large or complex files."
  }
  if (errorLower.includes('dimension') || errorLower.includes('room')) {
    return "We couldn't extract enough information from your blueprint to complete the analysis."
  }
  if (errorLower.includes('quality') || errorLower.includes('resolution')) {
    return "The blueprint quality is too low for accurate analysis. We need clearer images to identify rooms and dimensions."
  }
  if (errorLower.includes('api') || errorLower.includes('gpt')) {
    return "Our AI service is temporarily unavailable. This is usually resolved quickly."
  }
  
  // Default message
  return "The analysis encountered an unexpected issue. Our team has been notified."
}

function getErrorSuggestions(error: string | undefined): string[] {
  if (!error) return [
    "Try uploading a different blueprint",
    "Ensure your file is a PDF under 10MB",
    "Contact support if the issue persists"
  ]
  
  const errorLower = error.toLowerCase()
  
  if (errorLower.includes('pdf') || errorLower.includes('file')) {
    return [
      "Ensure your file is a valid PDF document",
      "Try re-saving the PDF from the original source",
      "Check that the file isn't password-protected",
      "Make sure the file is under 10MB"
    ]
  }
  
  if (errorLower.includes('timeout')) {
    return [
      "Try uploading a smaller file (under 5MB works best)",
      "Split multi-floor plans into separate files",
      "Remove unnecessary pages from the PDF",
      "Try again during off-peak hours"
    ]
  }
  
  if (errorLower.includes('dimension') || errorLower.includes('room')) {
    return [
      "Ensure room labels and dimensions are clearly visible",
      "Upload architectural floor plans rather than 3D renders",
      "Include a scale or dimension reference",
      "Avoid heavily stylized or artistic blueprints"
    ]
  }
  
  if (errorLower.includes('quality') || errorLower.includes('resolution')) {
    return [
      "Scan blueprints at 300 DPI or higher",
      "Ensure text and lines are sharp and clear",
      "Avoid photos of blueprints - use scans instead",
      "Check that the PDF isn't heavily compressed"
    ]
  }
  
  if (errorLower.includes('api') || errorLower.includes('gpt')) {
    return [
      "Wait a few minutes and try again",
      "Check our status page for service updates",
      "Try during off-peak hours if the issue persists"
    ]
  }
  
  // Default suggestions
  return [
    "Ensure your blueprint is a clear, standard floor plan",
    "Check that room labels and dimensions are visible",
    "Try a different file or format",
    "Contact support with your Job ID for assistance"
  ]
}

export default function AnalyzingPage() {
  const router = useRouter()
  const { jobId } = router.query
  const { data: session } = useSession()
  const [currentFactIndex, setCurrentFactIndex] = useState(0)
  const [startTime] = useState(Date.now())
  const [showShareModal, setShowShareModal] = useState(false)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [displayProgress, setDisplayProgress] = useState(0)
  const [currentStatusMessage, setCurrentStatusMessage] = useState(0)
  
  useEffect(() => {
    // Get email from cookie if not logged in
    if (!session?.user?.email) {
      const email = Cookies.get('user_email')
      if (email) {
        setUserEmail(email)
      }
    }
  }, [session])
  
  // Poll job status every 2 seconds
  const { data: jobStatus, error, mutate } = useSWR<JobStatus>(
    jobId ? jobId as string : null,
    apiHelpers.getJobStatus,
    {
      refreshInterval: 2000,
      refreshWhenHidden: false,
      refreshWhenOffline: false,
      revalidateOnFocus: true,
      onError: (error) => {
        console.error('Error fetching job status:', error)
      }
    }
  )
  
  // Rotate facts every 4 seconds
  useEffect(() => {
    if (jobStatus?.status === 'processing' || jobStatus?.status === 'pending') {
      const interval = setInterval(() => {
        setCurrentFactIndex((prev) => (prev + 1) % hvacFacts.length)
      }, 4000)
      return () => clearInterval(interval)
    }
  }, [jobStatus?.status])

  // Smooth progress animation
  useEffect(() => {
    if (jobStatus?.status === 'pending') {
      // Start at 0 and quickly move to 15%
      setDisplayProgress(0)
      setTimeout(() => setDisplayProgress(15), 100)
    } else if (jobStatus?.status === 'processing') {
      // Smooth increase from 15% to 90% over time
      setDisplayProgress(15)
      const targetProgress = 90
      const duration = 45000 // 45 seconds
      const startTime = Date.now()
      
      const interval = setInterval(() => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(elapsed / duration, 1)
        
        // Easing function for more natural feel
        const easeOutQuart = 1 - Math.pow(1 - progress, 4)
        const currentProgress = 15 + (targetProgress - 15) * easeOutQuart
        
        // Add small random variations for realism
        const variation = (Math.random() - 0.5) * 2
        setDisplayProgress(Math.min(currentProgress + variation, 90))
        
        if (progress >= 1) {
          clearInterval(interval)
        }
      }, 100)
      
      return () => clearInterval(interval)
    } else if (jobStatus?.status === 'completed') {
      // Smooth transition to 100%
      setDisplayProgress(100)
    } else if (jobStatus?.status === 'failed') {
      // Keep at current progress
    }
  }, [jobStatus?.status])

  // Rotate technical status messages
  useEffect(() => {
    if (jobStatus?.status === 'processing') {
      const interval = setInterval(() => {
        setCurrentStatusMessage((prev) => (prev + 1) % technicalStatusMessages.length)
      }, 3000)
      return () => clearInterval(interval)
    }
  }, [jobStatus?.status])

  
  const getProcessingStages = (status: string): ProcessingStage[] => {
    return [
      {
        title: "Reading Blueprint",
        description: "Extracting geometry and text from your PDF",
        status: status === 'pending' ? 'active' : 'completed',
        stats: status === 'pending' ? "Initializing..." : "PDF parsed"
      },
      {
        title: "AI Analysis",
        description: "Identifying rooms, windows, and dimensions using GPT-4",
        status: status === 'processing' ? 'active' : status === 'completed' ? 'completed' : 'pending',
        stats: status === 'processing' ? "Processing with AI..." : status === 'completed' ? "Analysis complete" : "Awaiting upload"
      },
      {
        title: "Load Calculations",
        description: "Computing Manual J heating and cooling loads",
        status: status === 'completed' ? 'completed' : 'pending',
        stats: status === 'completed' ? "Calculations done" : "Awaiting room data"
      },
      {
        title: "Equipment Sizing",
        description: "Recommending HVAC system specifications",
        status: status === 'completed' ? 'completed' : 'pending',
        stats: status === 'completed' ? "Report ready" : "Final step"
      }
    ]
  }
  
  const getOverallProgress = (status: string): number => {
    switch (status) {
      case 'pending': return 25
      case 'processing': return 65
      case 'completed': return 100
      case 'failed': return 0
      default: return 0
    }
  }
  
  const getElapsedTime = (): string => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000)
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }
  
  if (!jobId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Invalid Job ID</h1>
          <button 
            onClick={() => router.push('/')}
            className="btn-primary"
          >
            Return Home
          </button>
        </div>
      </div>
    )
  }
  
  if (error) {
    const errorMessage = error?.message || 'Unknown error occurred'
    const isBackendError = errorMessage.includes('HTTP 500') || errorMessage.includes('Backend error')
    
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-2xl">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Analysis Error</h1>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-sm font-mono text-red-800 mb-2">
              {isBackendError ? 'Backend 500 –' : 'Error –'} {errorMessage}
            </p>
            <p className="text-xs text-red-600">
              Please copy this error message if you need support.
            </p>
          </div>
          <p className="text-gray-600 mb-6">
            We encountered an error while processing your blueprint. You can retry or upload a new blueprint.
          </p>
          <div className="space-x-4">
            <button 
              onClick={() => router.push('/')}
              className="btn-primary"
            >
              Upload New Blueprint
            </button>
            <button 
              onClick={() => mutate()}
              className="btn-secondary"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }
  
  if (!jobStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analysis status...</p>
        </div>
      </div>
    )
  }
  
  return (
    <>
      <Head>
        <title>Analyzing Blueprint - AutoHVAC</title>
        <meta name="description" content="Your HVAC blueprint is being analyzed" />
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
              <div className="text-sm text-gray-500">
                Job ID: {jobId}
              </div>
            </div>
          </div>
        </nav>
        
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            {/* Status Header */}
            <div className="text-center p-8 bg-gradient-to-r from-brand-50 to-blue-50">
              <div className="mb-6">
                <div className="w-20 h-20 mx-auto mb-4 relative">
                  {jobStatus.status === 'completed' ? (
                    <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
                      <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : jobStatus.status === 'failed' ? (
                    <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center">
                      <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </div>
                  ) : (
                    <div className="w-20 h-20 bg-brand-100 rounded-full flex items-center justify-center animate-pulse">
                      <svg className="w-10 h-10 text-brand-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                      </svg>
                    </div>
                  )}
                </div>
              </div>
              
              <h1 className="text-3xl font-bold text-brand-700 mb-4">
                {jobStatus.status === 'completed' ? 'Analysis Complete!' :
                 jobStatus.status === 'failed' ? 'Analysis Failed' :
                 'Analyzing Your Blueprint'}
              </h1>
              
              {jobStatus.status === 'processing' && (
                <div className="mb-6">
                  <p className="text-gray-600 mb-3">
                    Our AI is carefully examining your blueprint to extract room dimensions, 
                    detect HVAC requirements, and calculate precise load requirements.
                  </p>
                  <p className="text-sm text-brand-600 font-medium animate-pulse">
                    {technicalStatusMessages[currentStatusMessage]}
                  </p>
                </div>
              )}
              
              <div className="flex justify-center items-center space-x-6 text-sm text-gray-500">
                <div>Elapsed: {getElapsedTime()}</div>
                <div>•</div>
                <div>Job: {jobId}</div>
              </div>
            </div>
            
            {/* Content */}
            <div className="p-8">
              {jobStatus.status === 'failed' ? (
                <div className="space-y-6">
                  {/* Friendly Error Message */}
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <svg className="w-6 h-6 text-amber-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-amber-900 mb-2">
                          We couldn't complete the analysis
                        </h3>
                        <p className="text-amber-800 mb-4">
                          {getErrorMessage(jobStatus.error)}
                        </p>
                        
                        {/* Helpful suggestions based on error type */}
                        <div className="bg-white bg-opacity-50 rounded-lg p-4 space-y-2">
                          <p className="text-sm font-medium text-amber-900">Here's what you can try:</p>
                          <ul className="text-sm text-amber-700 space-y-1 ml-4">
                            {getErrorSuggestions(jobStatus.error).map((suggestion, idx) => (
                              <li key={idx} className="flex items-start">
                                <span className="text-amber-500 mr-2">•</span>
                                <span>{suggestion}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Technical Details (Collapsible) */}
                  {jobStatus.error && (
                    <details className="bg-gray-50 rounded-lg p-4">
                      <summary className="cursor-pointer text-sm text-gray-600 font-medium hover:text-gray-800">
                        Technical details for support
                      </summary>
                      <div className="mt-3 p-3 bg-white rounded border border-gray-200">
                        <code className="text-xs text-gray-600 break-all">
                          Error: {jobStatus.error}
                          <br />
                          Job ID: {jobId}
                          <br />
                          Time: {new Date().toISOString()}
                        </code>
                      </div>
                    </details>
                  )}

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <button 
                      onClick={() => router.push('/')}
                      className="btn-primary"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Upload New Blueprint
                    </button>
                    <button 
                      onClick={() => router.push('/dashboard')}
                      className="btn-secondary"
                    >
                      View Dashboard
                    </button>
                    <button 
                      onClick={() => window.open('mailto:support@autohvac.ai?subject=Analysis Failed - ' + jobId, '_blank')}
                      className="btn-text text-gray-600"
                    >
                      Contact Support
                    </button>
                  </div>

                  {/* Educational Note */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div className="text-sm text-blue-800">
                        <p className="font-medium mb-1">Pro tip for best results:</p>
                        <p>Upload clear, high-resolution floor plans (300+ DPI) with visible room labels and dimensions. Avoid 3D renders, photos, or heavily compressed images.</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : jobStatus.status === 'completed' ? (
                <div>
                  {/* Show results immediately */}
                  <ResultsPreview 
                    result={jobStatus.result}
                    userEmail={userEmail}
                  />
                  
                  {/* Action buttons */}
                  <div className="flex flex-col sm:flex-row gap-3 justify-center mt-8">
                    {session ? (
                      <>
                        <button 
                          onClick={() => router.push('/dashboard')}
                          className="btn-primary"
                        >
                          View Full Dashboard
                        </button>
                        <button 
                          onClick={() => setShowShareModal(true)}
                          className="btn-secondary"
                        >
                          Share Results
                        </button>
                      </>
                    ) : (
                      <>
                        <button 
                          onClick={() => setShowShareModal(true)}
                          className="btn-primary"
                        >
                          Share Results
                        </button>
                        <button 
                          onClick={() => router.push('/')}
                          className="btn-secondary"
                        >
                          Analyze Another Blueprint
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-8">
                  {/* Processing Stages */}
                  <div className="space-y-4">
                    {getProcessingStages(jobStatus.status).map((stage, index) => (
                      <ProcessingStage 
                        key={index}
                        title={stage.title}
                        description={stage.description}
                        status={stage.status}
                        stats={stage.stats}
                      />
                    ))}
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="space-y-2">
                    <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-brand-500 to-blue-500 h-3 rounded-full transition-all duration-300 ease-out"
                        style={{ width: `${displayProgress}%` }}
                      />
                    </div>
                    <p className="text-center text-sm text-gray-600">
                      {Math.round(displayProgress)}% Complete
                    </p>
                  </div>
                  
                  {/* Educational Content */}
                  <div className="border-t pt-8">
                    <EducationalFact 
                      fact={hvacFacts[currentFactIndex].fact}
                      icon={hvacFacts[currentFactIndex].icon}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Share Modal */}
      <ShareModal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        projectId={jobId as string}
        projectName={`HVAC Analysis ${jobId}`}
      />
    </>
  )
}