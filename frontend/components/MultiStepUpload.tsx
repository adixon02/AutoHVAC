import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { signIn, useSession } from 'next-auth/react'
import { apiHelpers } from '../lib/fetcher'
import { apiClient } from '../lib/api-client'
// AccountCreationModal no longer needed - using CompletionAccountGate after analysis
import Cookies from 'js-cookie'

// 🔒 ANTI-FRAUD: Generate device fingerprint for preventing multiple fake emails
function generateDeviceFingerprint(): string {
  const fingerprint = {
    screen: `${screen.width}x${screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    platform: navigator.platform,
    userAgent: navigator.userAgent.slice(0, 100), // Truncated for privacy
    colorDepth: screen.colorDepth,
    pixelRatio: window.devicePixelRatio || 1
  }
  
  // Create a stable hash of the fingerprint
  return btoa(JSON.stringify(fingerprint)).replace(/[^a-zA-Z0-9]/g, '').slice(0, 64)
}

interface ProjectData {
  projectName: string
  blueprintFile: File | null
  // Core Required Fields
  squareFootage: string  // User input - most critical for accuracy
  zipCode: string
  email: string
  
  // Optional Fields with Smart Defaults
  numberOfStories: '1' | '2' | '3+' | 'not_sure'
  heatingFuel: 'gas' | 'heat_pump' | 'electric' | 'not_sure'
  ductConfig: 'ducted_attic' | 'ducted_crawl' | 'ductless' | 'not_sure'
  windowPerformance: 'standard' | 'high_performance' | 'premium' | 'not_sure'
  buildingOrientation: 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW' | 'not_sure'
}

interface MultiStepUploadProps {
  isOpen: boolean
  onClose: () => void
  initialFile?: File | null
}

export default function MultiStepUpload({ isOpen, onClose, initialFile }: MultiStepUploadProps) {
  const router = useRouter()
  const { data: session } = useSession()
  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [emailStatus, setEmailStatus] = useState<'new' | 'lead' | 'user' | null>(null)
  
  // Check for saved email from session or cookie
  const savedEmail = session?.user?.email || (typeof window !== 'undefined' ? Cookies.get('user_email') || '' : '')
  
  const [projectData, setProjectData] = useState<ProjectData>({
    projectName: '',
    blueprintFile: null,
    // Core required fields
    squareFootage: '',
    zipCode: '',
    email: savedEmail, // Pre-fill email if we have it
    
    // Optional fields with smart defaults (most common for new construction)
    numberOfStories: '2', // Most common new construction
    heatingFuel: 'heat_pump', // Most common in new construction 2020+
    ductConfig: 'not_sure', // Let AI detect unless user knows
    windowPerformance: 'not_sure', // Let AI detect unless user knows  
    buildingOrientation: 'not_sure' // Let AI detect unless user knows
  })

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

  const updateProjectData = (updates: Partial<ProjectData>) => {
    setProjectData(prev => ({ ...prev, ...updates }))
  }

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
          {/* Step 1: Project Setup */}
          {currentStep === 1 && (
            <Step1ProjectSetup 
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              error={error}
              setError={setError}
            />
          )}

          {/* Step 2: Building Basics */}
          {currentStep === 2 && (
            <Step2BuildingBasics
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 3: Duct Configuration */}
          {currentStep === 3 && (
            <Step2DuctConfig
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 4: Heating System */}
          {currentStep === 4 && (
            <Step3HeatingSystem
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 5: ZIP Code Collection */}
          {currentStep === 5 && (
            <Step4ZipCode
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
              error={error}
              setError={setError}
            />
          )}

          {/* Step 6: Building Orientation */}
          {currentStep === 6 && (
            <Step5Orientation
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 7: Review */}
          {currentStep === 7 && (
            <Step6Review
              projectData={projectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 8: Email Collection (moved to end for micro-engagement) */}
          {currentStep === 8 && (
            <Step7EmailCollection
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

  async function handleFinalSubmit() {
    setIsLoading(true)
    setError(null)
    
    try {
      // Create FormData with enhanced user inputs for maximum load calculation accuracy
      const formData = new FormData()
      formData.append('file', projectData.blueprintFile!)
      formData.append('project_label', projectData.projectName)
      formData.append('email', projectData.email)
      formData.append('zip_code', projectData.zipCode)
      
      // 🎯 ENHANCED USER INPUTS: Critical data for accurate load calculations
      formData.append('square_footage', projectData.squareFootage)
      formData.append('number_of_stories', projectData.numberOfStories)
      formData.append('heating_fuel', projectData.heatingFuel)
      formData.append('duct_config', projectData.ductConfig)
      formData.append('window_performance', projectData.windowPerformance)
      formData.append('building_orientation', projectData.buildingOrientation)
      
      // 🔒 ANTI-FRAUD: Add device fingerprint to prevent multiple fake emails
      const deviceFingerprint = generateDeviceFingerprint()
      formData.append('device_fingerprint', deviceFingerprint)
      console.log('🔒 Device fingerprint generated:', deviceFingerprint.slice(0, 12) + '...')

      // Use the existing API helper that has proper endpoint and error handling
      const result = await apiHelpers.uploadBlueprint(formData)
      
      // Runtime guard: Ensure job_id is present (backend uses snake_case)
      if (!result.job_id) {
        throw new Error('Upload route returned no job_id - API contract violation')
      }
      
      // Set user email cookie so dashboard recognizes the user
      Cookies.set('user_email', projectData.email, { expires: 30 }) // 30 days
      
      // Redirect to analyzing page
      router.push(`/analyzing/${result.job_id}`)
      handleClose()
      
    } catch (error: any) {
      console.error('Upload error:', error)
      
      // Check if it's a PaymentRequiredError from the fetcher
      if (error.name === 'PaymentRequiredError') {
        // Store email for the upgrade page
        Cookies.set('user_email', projectData.email, { expires: 30 })
        // Redirect to upgrade page for better conversion (not directly to checkout)
        router.push('/upgrade')
        return
      }
      
      // Check if it's a payment required error (402 or payment-related 500)
      if (error.response?.status === 402) {
        // Store email for the upgrade page
        Cookies.set('user_email', projectData.email, { expires: 30 })
        
        // Always redirect to upgrade page for better conversion
        // (not directly to checkout, even if URL is provided)
        router.push('/upgrade')
        return
      }
      
      // Also check for 500 errors that are payment-related
      if (error.response?.status === 500) {
        const errorDetail = error.response?.data?.detail
        if (errorDetail && (
          typeof errorDetail === 'string' && (
            errorDetail.includes('payment') || 
            errorDetail.includes('Payment') ||
            errorDetail.includes('stripe') ||
            errorDetail.includes('Stripe')
          )
        )) {
          // This is likely a payment-related error, redirect to upgrade
          Cookies.set('user_email', projectData.email, { expires: 30 })
          router.push('/upgrade')
          return
        }
      }
      
      // Final fallback - if we somehow have a 402 that wasn't caught above, still redirect
      if (error.response?.status === 402) {
        Cookies.set('user_email', projectData.email, { expires: 30 })
        router.push('/upgrade')
        return
      }
      
      setError(error.message || 'Upload failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }
}

// Step Components
function Step1ProjectSetup({ projectData, updateProjectData, onNext, error, setError }: any) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      updateProjectData({ blueprintFile: e.target.files[0] })
    }
  }

  const handleNext = () => {
    if (!projectData.projectName.trim()) {
      setError('Please enter a project name')
      return
    }
    if (!projectData.blueprintFile) {
      setError('Please select a blueprint file')
      return
    }
    setError(null)
    onNext()
  }

  return (
    <div className="space-y-6">
      {/* Project Name */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Project Name
        </label>
        <input
          type="text"
          value={projectData.projectName}
          onChange={(e) => updateProjectData({ projectName: e.target.value })}
          placeholder="e.g., Smith Residence, Downtown Office Building"
          maxLength={255}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
        />
        <p className="mt-2 text-sm text-gray-500">
          This helps you identify the project in your dashboard
        </p>
      </div>

      {/* Blueprint Upload */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Blueprint File
        </label>
        <div className="relative">
          <input
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.png,.jpg,.jpeg"
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="w-full border-2 border-dashed border-brand-200 rounded-xl p-8 text-center hover:border-brand-500 transition-colors cursor-pointer block"
          >
            {projectData.blueprintFile ? (
              <div className="flex items-center justify-center">
                <svg className="w-8 h-8 text-brand-700 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-brand-700 font-medium">{projectData.blueprintFile.name}</span>
              </div>
            ) : (
              <div>
                <svg className="w-12 h-12 text-brand-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-brand-700 font-medium mb-2">
                  Drop your blueprint here or click to browse
                </p>
                <p className="text-gray-500 text-sm">
                  Supports PDF, PNG, JPG, JPEG files (max 50MB)
                </p>
              </div>
            )}
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Please Complete Setup</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Continue Button */}
      <button
        onClick={handleNext}
        className="w-full btn-primary text-lg py-4"
      >
        Continue
      </button>
    </div>
  )
}

function Step7EmailCollection({ projectData, updateProjectData, onPrev, onSubmit, isLoading, error, setError }: any) {
  const { data: session } = useSession()
  const router = useRouter()
  const savedEmail = session?.user?.email || (typeof window !== 'undefined' ? Cookies.get('user_email') || '' : '')
  const isReturningUser = savedEmail && savedEmail === projectData.email
  // Account modal no longer needed - using completion gate instead
  
  const handleSubmit = async () => {
    if (!projectData.email.trim()) {
      setError('Please enter your email address')
      return
    }
    if (!/\S+@\S+\.\S+/.test(projectData.email)) {
      setError('Please enter a valid email address')
      return
    }
    setError(null)
    
    try {
      // Simplified flow: Just capture the lead and continue
      await apiClient.captureLead({
        email: projectData.email,
        marketing_consent: true,
        project_id: undefined // Will be set after upload
      })
      
      // Save email to cookie for later use
      Cookies.set('user_email', projectData.email, { expires: 365 })
      
      // Continue to upload and analysis
      onSubmit()
    } catch (err: any) {
      console.error('Lead capture error:', err)
      setError('Failed to process email. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      {/* Welcome Back Message */}
      {isReturningUser && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-sm font-medium text-green-800">Welcome back!</h4>
              <p className="text-sm text-green-700 mt-1">
                We've pre-filled your email. Just click continue to proceed.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Email Input */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Email Address
        </label>
        <input
          type="email"
          value={projectData.email}
          onChange={(e) => updateProjectData({ email: e.target.value })}
          placeholder="your@email.com"
          className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
        />
        <p className="mt-2 text-sm text-gray-500">
          {isReturningUser 
            ? '🎉 As a returning user, you know the drill! We\'ll email your analysis when it\'s ready.'
            : '✨ Your first blueprint analysis is completely free! No password or verification required.'
          }
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Please Complete</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 px-6 py-3 border border-gray-300 rounded-xl font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={handleSubmit}
          disabled={isLoading}
          className="flex-1 btn-primary text-lg py-3"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            'Start Analysis'
          )}
        </button>
      </div>
      
      {/* Account creation now happens after analysis completion */}
    </div>
  )
}

function Step2BuildingBasics({ projectData, updateProjectData, onNext, onPrev }: any) {
  const [error, setError] = useState('')

  const validateAndNext = () => {
    // Validate square footage is provided
    if (!projectData.squareFootage || projectData.squareFootage.trim() === '') {
      setError('Please enter the square footage of your building')
      return
    }
    
    // Validate square footage is a reasonable number
    const sqft = parseFloat(projectData.squareFootage)
    if (isNaN(sqft) || sqft < 200 || sqft > 50000) {
      setError('Please enter a valid square footage between 200 and 50,000 sq ft')
      return
    }
    
    setError('')
    onNext()
  }

  return (
    <div className="space-y-6">
      {/* Square Footage Input - Most Critical Field */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          Square Footage <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type="number"
            value={projectData.squareFootage}
            onChange={(e) => updateProjectData({ squareFootage: e.target.value })}
            placeholder="1,853"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors pr-16"
          />
          <span className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm">
            sq ft
          </span>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          💡 This is the most critical measurement for accurate load calculations. Most homes are 1,200-3,000 sq ft.
        </p>
      </div>

      {/* Number of Stories - Simple Selection */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-3">
          Number of Stories
        </label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: '1', label: '1 Story', icon: '🏠' },
            { value: '2', label: '2 Stories', icon: '🏘️' },
            { value: '3+', label: '3+ Stories', icon: '🏢' }
          ].map((option) => (
            <label
              key={option.value}
              className={`relative flex flex-col items-center p-4 border-2 rounded-xl cursor-pointer transition-all ${
                projectData.numberOfStories === option.value
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="numberOfStories"
                value={option.value}
                checked={projectData.numberOfStories === option.value}
                onChange={(e) => updateProjectData({ numberOfStories: e.target.value })}
                className="sr-only"
              />
              <span className="text-2xl mb-2">{option.icon}</span>
              <span className="text-sm font-medium text-center">{option.label}</span>
            </label>
          ))}
        </div>
        <p className="mt-2 text-sm text-gray-500">
          🎯 This helps us calculate room-by-room loads and multi-story air distribution accurately.
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Required Information</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 px-6 py-3 border border-gray-300 rounded-xl font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={validateAndNext}
          className="flex-1 btn-primary text-lg py-3"
        >
          Continue →
        </button>
      </div>
    </div>
  )
}

function Step2DuctConfig({ projectData, updateProjectData, onNext, onPrev }: any) {
  const ductOptions = [
    { 
      value: 'ducted_attic', 
      label: 'Ducted – Attic', 
      description: 'Traditional ductwork installed in attic space',
      icon: '🏠'
    },
    { 
      value: 'ducted_crawl', 
      label: 'Ducted – Crawl Space', 
      description: 'Traditional ductwork installed in crawl space',
      icon: '🏗️'
    },
    { 
      value: 'ductless', 
      label: 'Ductless / Mini-split', 
      description: 'Individual room units with no central ductwork',
      icon: '❄️'
    }
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {ductOptions.map((option) => (
          <label 
            key={option.value}
            className={`flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${
              projectData.ductConfig === option.value 
                ? 'border-brand-500 bg-brand-50' 
                : 'border-gray-200 hover:border-brand-300'
            }`}
          >
            <input
              type="radio"
              name="duct_config"
              value={option.value}
              checked={projectData.ductConfig === option.value}
              onChange={(e) => updateProjectData({ ductConfig: e.target.value })}
              className="w-5 h-5 text-brand-600 mt-0.5 mr-4"
            />
            <div className="text-2xl mr-4">{option.icon}</div>
            <div>
              <div className="font-medium text-gray-900">{option.label}</div>
              <div className="text-sm text-gray-600 mt-1">{option.description}</div>
            </div>
          </label>
        ))}
      </div>

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 btn-secondary text-lg py-4"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="flex-1 btn-primary text-lg py-4"
        >
          Next: Heating System
        </button>
      </div>
    </div>
  )
}

function Step3HeatingSystem({ projectData, updateProjectData, onNext, onPrev }: any) {
  const heatingOptions = [
    { 
      value: 'gas', 
      label: 'Natural Gas Furnace', 
      description: 'Traditional gas-fired heating system',
      icon: '🔥'
    },
    { 
      value: 'heat_pump', 
      label: 'Heat Pump', 
      description: 'Electric heat pump for both heating and cooling',
      icon: '⚡'
    },
    { 
      value: 'electric', 
      label: 'Electric Resistance', 
      description: 'Electric baseboard or forced air heating',
      icon: '🔌'
    }
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {heatingOptions.map((option) => (
          <label 
            key={option.value}
            className={`flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${
              projectData.heatingFuel === option.value 
                ? 'border-brand-500 bg-brand-50' 
                : 'border-gray-200 hover:border-brand-300'
            }`}
          >
            <input
              type="radio"
              name="heating_fuel"
              value={option.value}
              checked={projectData.heatingFuel === option.value}
              onChange={(e) => updateProjectData({ heatingFuel: e.target.value })}
              className="w-5 h-5 text-brand-600 mt-0.5 mr-4"
            />
            <div className="text-2xl mr-4">{option.icon}</div>
            <div>
              <div className="font-medium text-gray-900">{option.label}</div>
              <div className="text-sm text-gray-600 mt-1">{option.description}</div>
            </div>
          </label>
        ))}
      </div>

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 btn-secondary text-lg py-4"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="flex-1 btn-primary text-lg py-4"
        >
          Next: Project Location
        </button>
      </div>
    </div>
  )
}

function Step4ZipCode({ projectData, updateProjectData, onNext, onPrev, error, setError }: any) {
  const handleNext = () => {
    if (!projectData.zipCode.trim()) {
      setError('Please enter a ZIP code')
      return
    }
    if (!/^\d{5}$/.test(projectData.zipCode.trim())) {
      setError('ZIP code must be exactly 5 digits')
      return
    }
    setError(null)
    onNext()
  }

  return (
    <div className="space-y-6">
      {/* ZIP Code Input */}
      <div>
        <label className="block text-sm font-medium text-brand-700 mb-2">
          ZIP Code
        </label>
        <input
          type="text"
          value={projectData.zipCode}
          onChange={(e) => updateProjectData({ zipCode: e.target.value.replace(/\D/g, '').slice(0, 5) })}
          placeholder="12345"
          maxLength={5}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors text-center text-xl font-mono"
        />
        <p className="mt-2 text-sm text-gray-500">
          We use this for accurate climate data and HVAC sizing calculations
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Please Enter ZIP Code</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 btn-secondary text-lg py-4"
        >
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 btn-primary text-lg py-4"
        >
          Continue
        </button>
      </div>
    </div>
  )
}

function Step5Orientation({ projectData, updateProjectData, onNext, onPrev }: any) {
  const orientations = [
    { value: 'N', label: 'North', icon: '⬆️' },
    { value: 'NE', label: 'Northeast', icon: '↗️' },
    { value: 'E', label: 'East', icon: '➡️' },
    { value: 'SE', label: 'Southeast', icon: '↘️' },
    { value: 'S', label: 'South', icon: '⬇️' },
    { value: 'SW', label: 'Southwest', icon: '↙️' },
    { value: 'W', label: 'West', icon: '⬅️' },
    { value: 'NW', label: 'Northwest', icon: '↖️' },
    { value: 'unknown', label: 'Not sure', icon: '🧭', subtitle: "We'll estimate for you" }
  ]

  const handleNext = () => {
    if (!projectData.buildingOrientation) {
      // Default to unknown if not selected
      updateProjectData({ buildingOrientation: 'unknown' })
    }
    onNext()
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-gray-600 mb-6">
          Knowing your building's orientation helps us calculate accurate solar heat gains for each room, 
          improving system sizing by up to 20%.
        </p>
        
        <div className="grid grid-cols-2 gap-3">
          {orientations.slice(0, 8).map(orientation => (
            <button
              key={orientation.value}
              onClick={() => updateProjectData({ buildingOrientation: orientation.value })}
              className={`p-4 border-2 rounded-xl transition-all ${
                projectData.buildingOrientation === orientation.value 
                  ? 'border-brand-600 bg-brand-50 shadow-md' 
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-center">
                <span className="text-2xl mr-2">{orientation.icon}</span>
                <span className="font-medium">{orientation.label}</span>
              </div>
            </button>
          ))}
          
          {/* Not sure option - spans 2 columns */}
          <button
            onClick={() => updateProjectData({ buildingOrientation: 'unknown' })}
            className={`col-span-2 p-4 border-2 rounded-xl transition-all ${
              projectData.buildingOrientation === 'unknown' 
                ? 'border-brand-600 bg-brand-50 shadow-md' 
                : 'border-gray-200 hover:border-gray-300 bg-gray-50'
            }`}
          >
            <div className="flex flex-col items-center justify-center">
              <div className="flex items-center">
                <span className="text-2xl mr-2">{orientations[8].icon}</span>
                <span className="font-medium">{orientations[8].label}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{orientations[8].subtitle}</p>
            </div>
          </button>
        </div>
        
        <div className="mt-4 space-y-2">
          <p className="text-xs text-gray-500 text-center">
            Tip: Face the front door and note which compass direction you're looking at
          </p>
          <p className="text-xs text-gray-400 text-center">
            Selecting "Not sure" will use climate-based estimates, affecting accuracy by ~5-10%
          </p>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 btn-secondary text-lg py-4"
        >
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 btn-primary text-lg py-4"
        >
          Continue
        </button>
      </div>
    </div>
  )
}

function Step6Review({ projectData, onNext, onPrev }: any) {
  return (
    <div className="space-y-6">
      {/* Review Summary */}
      <div className="bg-gray-50 rounded-xl p-6 space-y-4">
        <h3 className="font-medium text-brand-700 mb-4">Review Your Project Details</h3>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Project Name</span>
            <span className="text-sm font-medium text-gray-900">{projectData.projectName}</span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Blueprint File</span>
            <span className="text-sm font-medium text-gray-900">{projectData.blueprintFile?.name}</span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Square Footage</span>
            <span className="text-sm font-medium text-gray-900">{projectData.squareFootage ? `${projectData.squareFootage} sq ft` : 'Not specified'}</span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Number of Stories</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.numberOfStories === '1' && '1 Story'}
              {projectData.numberOfStories === '2' && '2 Stories'}
              {projectData.numberOfStories === '3+' && '3+ Stories'}
              {!projectData.numberOfStories && 'Not specified'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Duct Configuration</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.ductConfig === 'ducted_attic' && 'Ducted – Attic'}
              {projectData.ductConfig === 'ducted_crawl' && 'Ducted – Crawl Space'}
              {projectData.ductConfig === 'ductless' && 'Ductless / Mini-split'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Heating System</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.heatingFuel === 'gas' && 'Natural Gas Furnace'}
              {projectData.heatingFuel === 'heat_pump' && 'Heat Pump'}
              {projectData.heatingFuel === 'electric' && 'Electric Resistance'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">ZIP Code</span>
            <span className="text-sm font-medium text-gray-900">{projectData.zipCode}</span>
          </div>
          
          <div className="flex justify-between items-center py-2">
            <span className="text-sm text-gray-600">Building Orientation</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.buildingOrientation === 'N' && 'North'}
              {projectData.buildingOrientation === 'NE' && 'Northeast'}
              {projectData.buildingOrientation === 'E' && 'East'}
              {projectData.buildingOrientation === 'SE' && 'Southeast'}
              {projectData.buildingOrientation === 'S' && 'South'}
              {projectData.buildingOrientation === 'SW' && 'Southwest'}
              {projectData.buildingOrientation === 'W' && 'West'}
              {projectData.buildingOrientation === 'NW' && 'Northwest'}
              {projectData.buildingOrientation === 'unknown' && '🧭 Not sure (will estimate)'}
              {!projectData.buildingOrientation && 'Not specified'}
            </span>
          </div>
        </div>
      </div>

      <div className="bg-brand-50 border border-brand-200 rounded-xl p-4">
        <p className="text-sm text-brand-800">
          <strong>Next step:</strong> Enter your email to receive your comprehensive HVAC analysis report.
        </p>
      </div>

      {/* Navigation Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={onPrev}
          className="flex-1 btn-secondary text-lg py-4"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="flex-1 btn-primary text-lg py-4"
        >
          Continue to Final Step
        </button>
      </div>
    </div>
  )
}

