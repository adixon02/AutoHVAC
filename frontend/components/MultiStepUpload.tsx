import React, { useState } from 'react'
import { useRouter } from 'next/router'
import { apiHelpers } from '../lib/fetcher'
import PaywallModal from './PaywallModal'
import Cookies from 'js-cookie'

interface ProjectData {
  projectName: string
  blueprintFile: File | null
  ductConfig: 'ducted_attic' | 'ducted_crawl' | 'ductless' | ''
  heatingFuel: 'gas' | 'heat_pump' | 'electric' | ''
  zipCode: string
  email: string
}

interface MultiStepUploadProps {
  isOpen: boolean
  onClose: () => void
}

export default function MultiStepUpload({ isOpen, onClose }: MultiStepUploadProps) {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPaywall, setShowPaywall] = useState(false)
  
  const [projectData, setProjectData] = useState<ProjectData>({
    projectName: '',
    blueprintFile: null,
    ductConfig: 'ducted_attic', // Pre-selected default
    heatingFuel: 'gas', // Pre-selected default
    zipCode: '',
    email: ''
  })

  const totalSteps = 5 // Still 5 steps but email moved to step 2

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
      ductConfig: 'ducted_attic',
      heatingFuel: 'gas',
      zipCode: '',
      email: ''
    })
    setError(null)
    onClose()
  }

  const updateProjectData = (updates: Partial<ProjectData>) => {
    setProjectData(prev => ({ ...prev, ...updates }))
  }

  if (!isOpen) return null

  // Show paywall if user hit their limit
  if (showPaywall) {
    return (
      <PaywallModal
        isOpen={true}
        onClose={() => {
          setShowPaywall(false)
          handleClose()
        }}
        userEmail={projectData.email}
      />
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div>
            <h2 className="text-2xl font-semibold text-brand-700">
              {currentStep === 1 && 'Start Your HVAC Analysis'}
              {currentStep === 2 && 'Where should we send your analysis?'}
              {currentStep === 3 && 'What type of ductwork?'}
              {currentStep === 4 && 'What heating system will you use?'}
              {currentStep === 5 && 'What\'s the project location?'}
            </h2>
            <p className="text-gray-600 mt-1">
              {currentStep === 1 && 'Upload your blueprint and give your project a name'}
              {currentStep === 2 && 'Enter your email to access your report'}
              {currentStep === 3 && 'This affects your system efficiency calculations'}
              {currentStep === 4 && 'This determines equipment recommendations'}
              {currentStep === 5 && 'We need the ZIP code for accurate climate data'}
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Indicator */}
        {currentStep > 1 && (
          <div className="px-6 py-4 border-b border-gray-100">
            <div className="flex items-center justify-center space-x-2">
              {Array.from({ length: 4 }, (_, i) => (
                <div
                  key={i}
                  className={`w-3 h-3 rounded-full ${
                    i < currentStep - 1 ? 'bg-brand-600' : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>
            <div className="text-center mt-2 text-sm text-gray-600">
              Step {currentStep - 1} of 4
            </div>
          </div>
        )}

        {/* Content */}
        <div className="p-6">
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

          {/* Step 2: Email Collection (moved earlier for better UX) */}
          {currentStep === 2 && (
            <Step2EmailCollection
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
              error={error}
              setError={setError}
            />
          )}

          {/* Step 3: Duct Configuration */}
          {currentStep === 3 && (
            <Step3DuctConfig
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 4: Heating System */}
          {currentStep === 4 && (
            <Step4HeatingSystem
              projectData={projectData}
              updateProjectData={updateProjectData}
              onNext={nextStep}
              onPrev={prevStep}
            />
          )}

          {/* Step 5: ZIP Code Collection */}
          {currentStep === 5 && (
            <Step5ZipCode
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
      // Create FormData with all collected information
      const formData = new FormData()
      formData.append('file', projectData.blueprintFile!)
      formData.append('project_label', projectData.projectName)
      formData.append('email', projectData.email)
      formData.append('zip_code', projectData.zipCode)
      formData.append('duct_config', projectData.ductConfig)
      formData.append('heating_fuel', projectData.heatingFuel)

      // Use the existing API helper that has proper endpoint and error handling
      const result = await apiHelpers.uploadBlueprint(formData)
      
      // Runtime guard: Ensure jobId is present
      if (!result.jobId) {
        throw new Error('Upload route returned no jobId - API contract violation')
      }
      
      // Set user email cookie so dashboard recognizes the user
      Cookies.set('user_email', projectData.email, { expires: 30 }) // 30 days
      
      // Redirect to analyzing page
      router.push(`/analyzing/${result.jobId}`)
      handleClose()
      
    } catch (error: any) {
      console.error('Upload error:', error)
      
      // Check if it's a payment required error
      if (error.response?.status === 402) {
        setShowPaywall(true)
        setIsLoading(false)
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

function Step2EmailCollection({ projectData, updateProjectData, onNext, onPrev, error, setError }: any) {
  const handleNext = () => {
    if (!projectData.email.trim()) {
      setError('Please enter your email address')
      return
    }
    if (!/\S+@\S+\.\S+/.test(projectData.email)) {
      setError('Please enter a valid email address')
      return
    }
    setError(null)
    onNext()
  }

  return (
    <div className="space-y-6">
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
          ✨ Your first blueprint analysis is completely free! No password or verification required.
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
          onClick={handleNext}
          className="flex-1 btn-primary text-lg py-3"
        >
          Continue
        </button>
      </div>
    </div>
  )
}

function Step3DuctConfig({ projectData, updateProjectData, onNext, onPrev }: any) {
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

function Step4HeatingSystem({ projectData, updateProjectData, onNext, onPrev }: any) {
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

function Step5ZipCode({ projectData, updateProjectData, onPrev, onSubmit, isLoading, error, setError }: any) {
  const handleSubmit = () => {
    if (!projectData.zipCode.trim()) {
      setError('Please enter a ZIP code')
      return
    }
    if (!/^\d{5}$/.test(projectData.zipCode.trim())) {
      setError('ZIP code must be exactly 5 digits')
      return
    }
    setError(null)
    onSubmit()
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
          onClick={handleSubmit}
          disabled={isLoading}
          className="flex-1 btn-primary text-lg py-4"
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
    </div>
  )
}

