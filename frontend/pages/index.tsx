import { useState, useEffect } from 'react'
import Hero from '../components/Hero'
import FeatureSteps from '../components/FeatureSteps'
import Testimonials from '../components/Testimonials'
import MultiStepUpload from '../components/MultiStepUpload'
import NavBar from '../components/NavBar'
import SEOHead from '../components/SEOHead'
import ROICalculator from '../components/ROICalculator'
import ContractorFAQ from '../components/ContractorFAQ'
import Cookies from 'js-cookie'

export default function Home() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [savedEmail, setSavedEmail] = useState<string | null>(null)
  const [initialFile, setInitialFile] = useState<File | null>(null)

  useEffect(() => {
    const email = Cookies.get('user_email')
    if (email) {
      setSavedEmail(email)
    }
  }, [])

  const handleGetStarted = (file?: File) => {
    if (file) {
      setInitialFile(file)
    }
    setIsUploadModalOpen(true)
  }

  // SEO data for homepage
  const seoData = {
    title: "AutoHVAC - AI Manual J Calculator | 60-Second HVAC Load Calculations",
    description: "Beat competitors with AI-powered Manual J calculations in 60 seconds vs 30+ minutes with desktop software. Upload blueprints, get professional ACCA reports instantly. First report free.",
    canonicalUrl: "https://autohvac.ai",
    image: "https://autohvac.ai/og-homepage.png",
    tags: ["AI HVAC calculator", "AI Manual J software", "instant load calculation", "AI blueprint analysis", "HVAC contractor software", "AI HVAC tools"],
    faqs: [
      {
        question: "How accurate are AutoHVAC's load calculations?",
        answer: "AutoHVAC uses ACCA Manual J 8th Edition procedures with AI-powered automation. Our calculations match professional desktop software while delivering results 100x faster in just 60 seconds."
      },
      {
        question: "Do I need to create an account to use AutoHVAC?",
        answer: "No, your first HVAC load calculation is completely free with no account required. Simply upload your plans and get instant results. Create an account only if you want to save reports or get additional calculations."
      },
      {
        question: "What file types can I upload for HVAC calculations?",
        answer: "AutoHVAC accepts PDF blueprints, CAD files (DWG, DXF), image files (JPG, PNG), and building plans in most common formats. Our AI can analyze any clear architectural drawing or floor plan."
      },
      {
        question: "How quickly will I receive my HVAC load report?",
        answer: "Most reports are generated in 60 seconds or less. Our AI analyzes your blueprints instantly and provides comprehensive Manual J calculations with equipment recommendations in under a minute."
      },
      {
        question: "Is AutoHVAC suitable for professional HVAC contractors?",
        answer: "Yes, AutoHVAC is designed for HVAC professionals, contractors, and engineers who need fast, accurate, ACCA-compliant load calculations. Our reports meet professional standards and include detailed room-by-room analysis."
      }
    ]
  };

  return (
    <>
      <SEOHead
        data={seoData}
        ogType="website"
      />
      <div className="min-h-screen">
      {/* Navigation */}
      <NavBar onGetStarted={handleGetStarted} />
      
      {/* Spacer for fixed navbar */}
      <div className="h-16"></div>

      {/* Welcome Back Banner */}
      {savedEmail && (
        <div className="bg-gradient-to-r from-brand-600 to-brand-700 text-white py-3">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium">
                Welcome back! Ready for another blueprint analysis?
              </span>
            </div>
            <button 
              onClick={() => handleGetStarted()}
              className="btn-small-secondary"
            >
              Start New Analysis
            </button>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <Hero onGetStarted={handleGetStarted} />

      {/* Feature Steps */}
      <FeatureSteps />

      {/* Competitive Comparison Section */}
      <section className="py-16 lg:py-24 bg-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
              Why <span className="text-brand-700">HVAC Pros Are Switching To AutoHVAC</span>
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Compare AutoHVAC's modern workflow with traditional Manual J software. See the difference in speed, convenience, and cost.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Traditional Way */}
            <div className="card p-8 border-2 border-red-200 bg-red-50">
              <div className="flex items-center mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mr-4">
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-semibold text-gray-900">Traditional Manual J Software</h3>
              </div>
              <ul className="space-y-3 text-gray-700">
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  30+ minutes per calculation
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Desktop-only, can't quote on-site
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Manual data entry for every room
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  $200+ per month licensing
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Requires training and certification
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Slow turnaround for quotes
                </li>
              </ul>
            </div>

            {/* AutoHVAC Way */}
            <div className="card p-8 border-2 border-brand-200 bg-brand-50">
              <div className="flex items-center mb-6">
                <div className="w-12 h-12 bg-brand-100 rounded-lg flex items-center justify-center mr-4">
                  <svg className="w-6 h-6 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-semibold text-gray-900">AutoHVAC</h3>
              </div>
              <ul className="space-y-3 text-gray-700">
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <strong>Accurate calculations in 60 seconds (or less)</strong>
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Works on phone, tablet, laptop - quote on-site
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Automatic blueprint analysis
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <strong>$97 per month</strong> (50% less than competitors)
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  No training required - intuitive interface
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <strong>Faster quote turnaround</strong>
                </li>
              </ul>
            </div>
          </div>

          <div className="text-center mt-12">
            <button 
              onClick={() => handleGetStarted()}
              className="btn-primary btn-lg"
            >
              Try AutoHVAC Free
            </button>
            <p className="text-sm text-gray-500 mt-3">No credit card required • First report completely free</p>
          </div>
        </div>
      </section>

      {/* ROI Calculator */}
      <ROICalculator onGetStarted={handleGetStarted} />

      {/* Testimonials */}
      <Testimonials />

      {/* Contractor FAQ */}
      <ContractorFAQ onGetStarted={handleGetStarted} />

      {/* Footer CTA */}
      <section className="relative py-16 lg:py-24 bg-gradient-to-br from-brand-700 to-brand-800 overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-600 rounded-full mix-blend-multiply filter blur-3xl opacity-30"></div>
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-brand-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20"></div>
        </div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6">
            Ready to modernize your HVAC workflow?
          </h2>
          <p className="text-xl text-brand-100 mb-8 max-w-3xl mx-auto">
            Join contractors who've upgraded from manual calculations to automated reports. 
            Get accurate Manual J calculations in 60 seconds instead of 30+ minutes.
          </p>
          <button 
            onClick={() => handleGetStarted()}
            className="btn-primary bg-white text-brand-700 hover:bg-brand-50 text-lg px-8 py-4"
          >
            Start Free Analysis
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-100 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="md:col-span-1">
              <div className="flex items-center mb-4">
                <div className="w-8 h-8 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center shadow-sm mr-3">
                  <span className="text-white font-bold text-sm">AH</span>
                </div>
                <div className="text-2xl font-bold text-brand-700">
                  AutoHVAC
                </div>
              </div>
              <p className="text-gray-600 text-sm">
                AI-powered HVAC load calculations and design for modern contractors.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-brand-700 mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><a href="#" className="hover:text-brand-700">Features</a></li>
                <li><a href="#" className="hover:text-brand-700">Pricing</a></li>
                <li><a href="#" className="hover:text-brand-700">API</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-brand-700 mb-4">Support</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><a href="#" className="hover:text-brand-700">Documentation</a></li>
                <li><a href="#" className="hover:text-brand-700">Help Center</a></li>
                <li><a href="#" className="hover:text-brand-700">Contact</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-brand-700 mb-4">Company</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><a href="#" className="hover:text-brand-700">About</a></li>
                <li><a href="#" className="hover:text-brand-700">Blog</a></li>
                <li><a href="#" className="hover:text-brand-700">Careers</a></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-200 text-center">
            <p className="text-gray-500 text-sm">
              © 2024 AutoHVAC. All rights reserved.
            </p>
          </div>
        </div>
      </footer>

      {/* Multi-Step Upload */}
      <MultiStepUpload 
        isOpen={isUploadModalOpen} 
        onClose={() => {
          setIsUploadModalOpen(false)
          setInitialFile(null)
        }}
        initialFile={initialFile}
      />
    </div>
    </>
  )
}