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
              Upload any blueprint.
              <span className="block text-brand-700">
                Get accurate Manual J calculations in <span className="underline">seconds</span>.
              </span>
            </h1>
            
            <p className="text-lg text-gray-600 mb-8 leading-relaxed">
              AutoHVAC uses advanced AI to analyze your architectural blueprints and generate 
              complete HVAC designs with load calculations, duct layouts, and equipment specifications.
            </p>
            
            {/* Stats */}
            <div className="grid grid-cols-3 gap-6 mb-8">
              <div className="text-center lg:text-left">
                <div className="text-2xl font-semibold text-gray-900">60s</div>
                <div className="text-sm text-gray-600">Complete Manual J</div>
              </div>
              <div className="text-center lg:text-left">
                <div className="text-2xl font-semibold text-gray-900">100%</div>
                <div className="text-sm text-gray-600">ACCA Compliant</div>
              </div>
              <div className="text-center lg:text-left">
                <div className="text-2xl font-semibold text-gray-900">Pro</div>
                <div className="text-sm text-gray-600">Quality Reports</div>
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
                <span className="text-sm text-gray-600">Works on Mobile</span>
              </div>
            </div>
          </div>
          
          {/* Right Column - Upload Zone with Animated Elements */}
          <div className="relative animate-slide-up">
            {/* Main Upload Card */}
            <div className="card p-8 max-w-md mx-auto">
              <div 
                className={`border-2 border-dashed rounded-xl transition-all duration-200 p-8 text-center cursor-pointer ${
                  isDragging 
                    ? 'border-brand-500 bg-brand-50 shadow-lg scale-[1.02]' 
                    : 'border-gray-200 hover:border-brand-400 hover:bg-gray-50'
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
                <div className="mx-auto w-16 h-16 bg-gradient-to-br from-brand-100 to-brand-200 rounded-xl flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                
                <h3 className="text-base font-semibold text-gray-900 mb-2">
                  Drop your blueprint here
                </h3>
                <p className="text-sm text-gray-500">
                  or click to browse from your computer
                </p>
              
                <div className="flex items-center justify-center gap-4 text-xs text-gray-400 mt-4">
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    PDF format
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    Max 100MB
                  </span>
                </div>
              </div>
              
              {/* Animated Progress Indicators */}
              <div className="mt-6 space-y-3">
                <div className="flex items-center justify-between p-3 bg-success-50 rounded-lg border border-success-100 animate-fade-in" style={{animationDelay: '0.5s'}}>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-success-500 rounded-full mr-3 animate-pulse"></div>
                    <span className="text-sm font-medium text-success-800">Manual J Complete</span>
                  </div>
                  <span className="text-success-600 text-xs font-medium">47s</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100 animate-fade-in" style={{animationDelay: '0.7s'}}>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-3 animate-pulse" style={{animationDelay: '0.2s'}}></div>
                    <span className="text-sm font-medium text-blue-800">Duct Layout Generated</span>
                  </div>
                  <span className="text-blue-600 text-xs font-medium">Ready</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-brand-50 rounded-lg border border-brand-100 animate-fade-in" style={{animationDelay: '0.9s'}}>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-brand-500 rounded-full mr-3 animate-pulse" style={{animationDelay: '0.4s'}}></div>
                    <span className="text-sm font-medium text-brand-800">Equipment Sized</span>
                  </div>
                  <span className="text-brand-600 text-xs font-medium">Optimized</span>
                </div>
              </div>
            </div>
            
            {/* Floating Animated Elements */}
            <div className="absolute -top-4 -right-4 bg-white rounded-xl shadow-lg p-3 animate-float" style={{animationDelay: '0.2s'}}>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-xs font-bold">5T</span>
                </div>
                <div>
                  <div className="text-xs font-semibold text-gray-900">5-Ton Unit</div>
                  <div className="text-xs text-gray-500">Auto-Selected</div>
                </div>
              </div>
            </div>
            
            <div className="absolute -bottom-4 -left-4 bg-white rounded-xl shadow-lg p-3 animate-float" style={{animationDelay: '0.8s'}}>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-success-500 to-success-600 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs font-semibold text-gray-900">Code Compliant</div>
                  <div className="text-xs text-gray-500">California Title 24</div>
                </div>
              </div>
            </div>
            
          </div>
        </div>
      </div>
      
      <style jsx>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-10px);
          }
        }
        .animate-float {
          animation: float 3s ease-in-out infinite;
        }
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