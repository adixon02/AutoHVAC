import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/router'
import { useSession } from 'next-auth/react'
import { apiHelpers } from '../lib/fetcher'
import Cookies from 'js-cookie'
import {
  Step1ProjectSetup,
  Step2BuildingBasics,
  Step3DuctConfig,
  Step4HeatingSystem,
  Step5ZipCode,
  Step6Orientation,
  Step7Review,
  Step8EmailCollection,
  type ProjectData
} from './upload-steps'


interface MultiStepUploadProps {
  isOpen: boolean
  onClose: () => void
  initialFile?: File | null
}

const MultiStepUpload = React.memo(function MultiStepUpload({ isOpen, onClose, initialFile }: MultiStepUploadProps) {
  const router = useRouter()
  const { data: session } = useSession()
  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  
  // Memoized saved email to prevent unnecessary re-renders
  const savedEmail = useMemo(() => 
    session?.user?.email || (typeof window !== 'undefined' ? Cookies.get('user_email') || '' : ''),
    [session?.user?.email]
  )
  
  const [projectData, setProjectData] = useState<ProjectData>(() => ({
    projectName: '',
    blueprintFile: null,
    squareFootage: '',
    zipCode: '',
    email: savedEmail,
    numberOfStories: '2',
    heatingFuel: 'heat_pump',
    ductConfig: 'not_sure',
    windowPerformance: 'not_sure',
    buildingOrientation: 'not_sure'
  }))

  const totalSteps = 8 // Enhanced with square footage and additional accuracy fields

  // Handle initial file when modal opens
  useEffect(() => {
    if (isOpen && initialFile) {
      setProjectData(prev => ({ ...prev, blueprintFile: initialFile }))
      // If we have a file, automatically advance to step 2
      if (currentStep === 1 && initialFile) {
        setCurrentStep(2)
      }
    }
  }, [isOpen, initialFile])

  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1)
      setError(null)
    }
  }

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
      setError(null)
    }
  }

  const handleClose = () => {
    setCurrentStep(1)
    setProjectData({
      projectName: '',
      blueprintFile: null,
      squareFootage: '',
      zipCode: '',
      email: '',
      numberOfStories: 'not_sure',
      heatingFuel: 'gas',
      ductConfig: 'ducted_attic',
      windowPerformance: 'not_sure',
      buildingOrientation: 'not_sure'
    })
    setError(null)
    onClose()
  }

  // Optimized update function with useCallback to prevent re-renders
  const updateProjectData = useCallback((updates: Partial<ProjectData>) => {
    setProjectData(prev => ({ ...prev, ...updates }))
  }, [])

  if (!isOpen) return null

  // Remove modal paywall - we'll redirect to full page instead

  return (
    <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100 bg-gray-25">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {currentStep === 1 && 'Start Your HVAC Analysis'}
              {currentStep === 2 && 'Tell us about your building'}
              {currentStep === 3 && 'What type of ductwork?'}
              {currentStep === 4 && 'What heating system will you use?'}
              {currentStep === 5 && 'What\'s the project location?'}
              {currentStep === 6 && 'Building Orientation'}
              {currentStep === 7 && 'Almost done!'}
              {currentStep === 8 && 'Where should we send your analysis?'}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {currentStep === 1 && 'Upload your blueprint and give your project a name'}
              {currentStep === 2 && 'Help us calculate your specific building loads accurately'}
              {currentStep === 3 && 'This affects your system efficiency calculations'}
              {currentStep === 4 && 'This determines equipment recommendations'}
              {currentStep === 5 && 'We need the ZIP code for accurate climate data'}
              {currentStep === 6 && 'Which direction does the front of your building face?'}
              {currentStep === 7 && 'Review your selections'}
              {currentStep === 8 && 'Enter your email to receive your HVAC analysis report'}
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="btn-icon hover:bg-gray-100 disabled:opacity-50 transition-all"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Indicator */}
        <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-25 border-b border-gray-100">
          <div className="flex items-center justify-between max-w-md mx-auto">
            {Array.from({ length: totalSteps }, (_, i) => (
              <React.Fragment key={i}>
                <div className="flex flex-col items-center relative">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300 ${
                      i < currentStep 
                        ? 'bg-brand-600 text-white' 
                        : i === currentStep - 1
                        ? 'bg-brand-100 text-brand-700 border-2 border-brand-600'
                        : 'bg-gray-100 text-gray-400 border border-gray-300'
                    }`}
                  >
                    {i < currentStep - 1 ? (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      i + 1
                    )}
                  </div>
                </div>
                {i < totalSteps - 1 && (
                  <div className={`flex-1 h-0.5 transition-all duration-500 ${
                    i < currentStep - 1 ? 'bg-brand-600' : 'bg-gray-200'
                  }`} />
                )}
              </React.Fragment>
            ))}
          </div>
          <div className="text-center mt-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
            Step {currentStep} of {totalSteps}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto">
          {/* Progress bar during upload */}
          {isLoading && uploadProgress > 0 && (
            <div className="mb-6">
              <div className="bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-brand-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 mt-2 text-center">
                {uploadProgress < 30 ? 'Preparing file...' : 
                 uploadProgress < 60 ? 'Uploading blueprint...' :
                 uploadProgress < 90 ? 'Processing data...' : 'Almost done...'}
              </p>
            </div>
          )}

          {/* Dynamic step rendering - only loads current step */}
          {currentStep === 1 && (
            <Step1ProjectSetup 
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              error={error}
              setError={setError}
            />
          )}

          {currentStep === 2 && (
            <Step2BuildingBasics
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {currentStep === 3 && (
            <Step3DuctConfig
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {currentStep === 4 && (
            <Step4HeatingSystem
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {currentStep === 5 && (
            <Step5ZipCode
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
              error={error}
              setError={setError}
            />
          )}

          {currentStep === 6 && (
            <Step6Orientation
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {currentStep === 7 && (
            <Step7Review
              projectData={projectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {currentStep === 8 && (
            <Step8EmailCollection
              projectData={projectData}
              updateProjectData={updateProjectData}
              onPrev={prevStep}
              onSubmit={() => handleFinalSubmit()}
              isLoading={isLoading}
              error={error}
              setError={setError}
            />
          )}
        </div>
      </div>
    </div>
  )

  // Optimized upload with progress feedback
  async function handleFinalSubmit() {
    setIsLoading(true)
    setError(null)
    setUploadProgress(0)
    
    try {
      // Optimistic UI: Start progress immediately
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev < 20) return prev + 2
          if (prev < 60) return prev + 1
          if (prev < 80) return prev + 0.5
          return prev
        })
      }, 100)

      // Create FormData - same structure as before (backend compatibility maintained)
      const formData = new FormData()
      formData.append('file', projectData.blueprintFile!)
      formData.append('project_label', projectData.projectName)
      formData.append('email', projectData.email)
      formData.append('zip_code', projectData.zipCode)
      formData.append('square_footage', projectData.squareFootage)
      formData.append('number_of_stories', projectData.numberOfStories)
      formData.append('heating_fuel', projectData.heatingFuel)
      formData.append('duct_config', projectData.ductConfig)
      formData.append('window_performance', projectData.windowPerformance)
      formData.append('building_orientation', projectData.buildingOrientation)
      
      setUploadProgress(70)
      
      const result = await apiHelpers.uploadBlueprint(formData)
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      
      if (!result.job_id) {
        throw new Error('Upload route returned no job_id - API contract violation')
      }
      
      Cookies.set('user_email', projectData.email, { expires: 30 })
      
      // Small delay for smooth progress completion
      setTimeout(() => {
        router.push(`/analyzing/${result.job_id}`)
        handleClose()
      }, 500)
      
    } catch (error: any) {
      setUploadProgress(0)
      console.error('Upload error:', error)
      
      if (error.name === 'PaymentRequiredError' || error.response?.status === 402) {
        Cookies.set('user_email', projectData.email, { expires: 30 })
        router.push('/upgrade')
        return
      }
      
      if (error.response?.status === 500) {
        const errorDetail = error.response?.data?.detail
        if (errorDetail && typeof errorDetail === 'string' && (
          errorDetail.includes('payment') || errorDetail.includes('Payment') ||
          errorDetail.includes('stripe') || errorDetail.includes('Stripe')
        )) {
          Cookies.set('user_email', projectData.email, { expires: 30 })
          router.push('/upgrade')
          return
        }
      }
      
      setError(error.message || 'Upload failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }
})

export default MultiStepUpload

