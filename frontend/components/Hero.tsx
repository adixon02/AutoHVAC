import { useState, useRef } from 'react'

interface HeroProps {
  onGetStarted: (file?: File) => void
}

export default function Hero({ onGetStarted }: HeroProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0 && files[0].type === 'application/pdf') {
      onGetStarted(files[0])
    }
  }

  const handleFileClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0 && files[0].type === 'application/pdf') {
      onGetStarted(files[0])
    }
  }

  return (
    <section className="relative overflow-hidden bg-white">
      {/* Background gradient mesh */}
      <div className="absolute inset-0 gradient-mesh opacity-30"></div>
      
      {/* Animated gradient orbs */}
      <div className="absolute top-0 -left-4 w-72 h-72 bg-brand-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
      <div className="absolute top-0 -right-4 w-72 h-72 bg-accent-orange rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-72 h-72 bg-brand-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left Column - Content */}
          <div className="text-center lg:text-left animate-fade-in">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-brand-50 border border-brand-200 mb-6">
              <span className="text-xs font-medium text-brand-700">New: AI-Powered Analysis</span>
              <svg className="w-3 h-3 ml-2 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
            
            <h1 className="display-md lg:display-lg text-gray-900 mb-6">
              Upload your blueprint.
              <span className="block text-brand-700">
                Get permit-ready HVAC plans in minutes.
              </span>
            </h1>
            
            <p className="text-lg text-gray-600 mb-8 leading-relaxed">
              AutoHVAC uses advanced AI to analyze your architectural blueprints and generate 
              complete HVAC designs with load calculations, duct layouts, and equipment specifications.
            </p>
            
            {/* Stats */}
            <div className="grid grid-cols-3 gap-6 mb-8">
              <div className="text-center lg:text-left">
                <div className="text-2xl font-semibold text-gray-900">95%</div>
                <div className="text-sm text-gray-600">Time Saved</div>
              </div>
              <div className="text-center lg:text-left">
                <div className="text-2xl font-semibold text-gray-900">10min</div>
                <div className="text-sm text-gray-600">Average Process</div>
              </div>
              <div className="text-center lg:text-left">
                <div className="text-2xl font-semibold text-gray-900">100%</div>
                <div className="text-sm text-gray-600">ACCA Compliant</div>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <button 
                onClick={() => onGetStarted()}
                className="btn-primary btn-lg group"
              >
                Start Free Analysis
                <svg className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
              <button className="btn-secondary btn-lg">
                View Sample Report
              </button>
            </div>
            
            {/* Trust badges */}
            <div className="flex items-center gap-6 mt-8 justify-center lg:justify-start">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm text-gray-600">ACCA Certified</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span className="text-sm text-gray-600">Secure & Private</span>
              </div>
            </div>
          </div>
          
          {/* Right Column - Upload Zone */}
          <div className="relative animate-slide-up">
            <div 
              className={`relative bg-white rounded-2xl border-2 border-dashed transition-all duration-200 p-12 text-center cursor-pointer ${
                isDragging 
                  ? 'border-brand-500 bg-brand-50 shadow-lg scale-[1.02]' 
                  : 'border-gray-300 hover:border-gray-400 hover:shadow-md'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={handleFileClick}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="hidden"
              />
              
              {/* Upload icon with animation */}
              <div className="mx-auto w-20 h-20 bg-gradient-to-br from-brand-100 to-brand-200 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <svg className="w-10 h-10 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Drop your blueprint here
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                or click to browse from your computer
              </p>
              
              <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  PDF format
                </span>
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  Max 100MB
                </span>
              </div>
              
              {/* Animated border gradient */}
              <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-r from-brand-500 via-accent-orange to-brand-500 opacity-0 group-hover:opacity-10 transition-opacity duration-500"></div>
              </div>
            </div>
            
            {/* Sample blueprints */}
            <div className="mt-6 flex items-center justify-center gap-4">
              <span className="text-sm text-gray-500">No blueprint? Try our</span>
              <button className="text-sm font-medium text-brand-600 hover:text-brand-700 underline underline-offset-4">
                sample files
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </section>
  )
}