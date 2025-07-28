import { useRouter } from 'next/router'
import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { apiHelpers } from '@/lib/fetcher'
import Head from 'next/head'
import AssumptionModal from '../../components/AssumptionModal'

interface JobStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: any
  error?: string
  assumptions_collected?: boolean
}

interface AssumptionValues {
  duct_config: 'ducted_attic' | 'ducted_crawl' | 'ductless' | ''
  heating_fuel: 'gas' | 'heat_pump' | 'electric' | ''
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

export default function AnalyzingPage() {
  const router = useRouter()
  const { jobId } = router.query
  const [currentFactIndex, setCurrentFactIndex] = useState(0)
  const [startTime] = useState(Date.now())
  const [showAssumptionModal, setShowAssumptionModal] = useState(false)
  const [submittingAssumptions, setSubmittingAssumptions] = useState(false)
  
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
  
  // Show assumption modal when processing and assumptions not collected
  useEffect(() => {
    if (jobStatus?.status === 'processing' && !jobStatus.assumptions_collected && !showAssumptionModal) {
      setShowAssumptionModal(true)
    }
  }, [jobStatus?.status, jobStatus?.assumptions_collected, showAssumptionModal])

  
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

  const handleAssumptionSubmit = async (values: AssumptionValues) => {
    if (!jobId) return
    
    setSubmittingAssumptions(true)
    try {
      const response = await fetch(`/api/jobs/${jobId}/assumptions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      })

      if (!response.ok) {
        throw new Error('Failed to submit assumptions')
      }

      setShowAssumptionModal(false)
      // Refresh job status to continue processing
      mutate()
    } catch (error) {
      console.error('Error submitting assumptions:', error)
      // TODO: Show error message to user
    } finally {
      setSubmittingAssumptions(false)
    }
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
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Analysis Error</h1>
          <p className="text-gray-600 mb-6">
            We encountered an error while processing your blueprint. Please try uploading again.
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
                <p className="text-gray-600 mb-6">
                  Our AI is carefully examining your blueprint to extract room dimensions, 
                  detect HVAC requirements, and calculate precise load requirements.
                </p>
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
                <div className="text-center">
                  <div className="p-6 bg-red-50 rounded-lg mb-6">
                    <h3 className="text-lg font-semibold text-red-800 mb-2">Analysis Failed</h3>
                    <p className="text-red-600">{jobStatus.error || 'An unknown error occurred'}</p>
                  </div>
                  <button 
                    onClick={() => router.push('/')}
                    className="btn-primary"
                  >
                    Try Again
                  </button>
                </div>
              ) : jobStatus.status === 'completed' ? (
                <div className="text-center">
                  <div className="p-6 bg-green-50 rounded-lg mb-6">
                    <h3 className="text-lg font-semibold text-green-800 mb-4">🎉 Analysis Complete!</h3>
                    {jobStatus.result && (
                      <div className="text-left space-y-2 text-sm text-green-700">
                        <div><strong>Rooms Detected:</strong> {jobStatus.result.zones?.length || 0}</div>
                        <div><strong>Total Heating Load:</strong> {jobStatus.result.heating_total || 0} BTU/hr</div>
                        <div><strong>Total Cooling Load:</strong> {jobStatus.result.cooling_total || 0} BTU/hr</div>
                      </div>
                    )}
                  </div>
                  <p className="text-gray-600 mb-4">
                    Your detailed HVAC analysis report is ready to view!
                  </p>
                  <button 
                    onClick={() => router.push('/dashboard')}
                    className="btn-primary"
                  >
                    View Dashboard
                  </button>
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
                    <div className="bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-gradient-to-r from-brand-500 to-blue-500 h-3 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${getOverallProgress(jobStatus.status)}%` }}
                      />
                    </div>
                    <p className="text-center text-sm text-gray-600">
                      {getOverallProgress(jobStatus.status)}% Complete
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

      {/* Assumption Modal */}
      <AssumptionModal
        isOpen={showAssumptionModal}
        onSubmit={handleAssumptionSubmit}
        onClose={() => setShowAssumptionModal(false)}
        isLoading={submittingAssumptions}
      />
    </>
  )
}