import { useState, useEffect } from 'react'
import Hero from '../components/Hero'
import FeatureSteps from '../components/FeatureSteps'
import Testimonials from '../components/Testimonials'
import MultiStepUpload from '../components/MultiStepUpload'
import NavBar from '../components/NavBar'
import Cookies from 'js-cookie'

export default function Home() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [savedEmail, setSavedEmail] = useState<string | null>(null)

  useEffect(() => {
    const email = Cookies.get('user_email')
    if (email) {
      setSavedEmail(email)
    }
  }, [])

  const handleGetStarted = () => {
    setIsUploadModalOpen(true)
  }

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <NavBar onGetStarted={handleGetStarted} />

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
              onClick={handleGetStarted}
              className="text-sm font-medium bg-white text-brand-700 px-4 py-1 rounded-lg hover:bg-brand-50 transition-colors"
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

      {/* Testimonials */}
      <Testimonials />

      {/* Footer CTA */}
      <section className="py-16 lg:py-24 bg-brand-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6">
            Ready to revolutionize your HVAC workflow?
          </h2>
          <p className="text-xl text-brand-100 mb-8 max-w-3xl mx-auto">
            Join thousands of professionals who've streamlined their blueprint analysis process.
          </p>
          <button 
            onClick={handleGetStarted}
            className="btn-primary bg-white text-brand-700 hover:bg-brand-50 text-lg px-8 py-4"
          >
            Start Free Analysis
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="md:col-span-1">
              <div className="text-2xl font-bold text-brand-700 mb-4">
                AutoHVAC
              </div>
              <p className="text-gray-600 text-sm">
                Automated HVAC load calculations and duct design for modern contractors.
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
        onClose={() => setIsUploadModalOpen(false)} 
      />
    </div>
  )
}