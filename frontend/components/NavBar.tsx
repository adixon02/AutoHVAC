import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import Cookies from 'js-cookie'

interface NavBarProps {
  onGetStarted?: () => void
  showGetStarted?: boolean
}

export default function NavBar({ onGetStarted, showGetStarted = true }: NavBarProps) {
  const router = useRouter()
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  useEffect(() => {
    // Check for user email in cookies
    const email = Cookies.get('user_email')
    setUserEmail(email || null)
  }, [])

  const handleSignOut = () => {
    Cookies.remove('user_email')
    setUserEmail(null)
    router.push('/')
  }

  const handleDashboardClick = () => {
    if (userEmail) {
      router.push(`/dashboard?email=${encodeURIComponent(userEmail)}`)
    }
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="text-2xl font-bold text-brand-700 hover:text-brand-800 transition-colors">
              AutoHVAC
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            {/* Navigation Links */}
            <div className="flex items-center space-x-6">
              <Link href="/#features" className="text-gray-600 hover:text-brand-700 transition-colors">
                Features
              </Link>
              <Link href="/#how-it-works" className="text-gray-600 hover:text-brand-700 transition-colors">
                How It Works
              </Link>
              <Link href="/#pricing" className="text-gray-600 hover:text-brand-700 transition-colors">
                Pricing
              </Link>
            </div>

            {/* User Section */}
            {userEmail ? (
              <div className="flex items-center space-x-4">
                <button
                  onClick={handleDashboardClick}
                  className="text-brand-600 hover:text-brand-700 font-medium transition-colors"
                >
                  Dashboard
                </button>
                <div className="flex items-center space-x-3">
                  <span className="text-sm text-gray-600 max-w-32 truncate" title={userEmail}>
                    {userEmail}
                  </span>
                  <button
                    onClick={handleSignOut}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                    title="Sign Out"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                  </button>
                </div>
              </div>
            ) : showGetStarted && onGetStarted ? (
              <button 
                onClick={onGetStarted}
                className="btn-primary"
              >
                Get Started
              </button>
            ) : null}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-gray-100 py-4">
            <div className="flex flex-col space-y-4">
              {/* Navigation Links */}
              <Link 
                href="/#features" 
                className="text-gray-600 hover:text-brand-700 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                Features
              </Link>
              <Link 
                href="/#how-it-works" 
                className="text-gray-600 hover:text-brand-700 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                How It Works
              </Link>
              <Link 
                href="/#pricing" 
                className="text-gray-600 hover:text-brand-700 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                Pricing
              </Link>

              {/* User Section */}
              {userEmail ? (
                <div className="pt-4 border-t border-gray-100">
                  <div className="text-sm text-gray-600 mb-2 truncate">
                    Signed in as: {userEmail}
                  </div>
                  <div className="flex flex-col space-y-2">
                    <button
                      onClick={() => {
                        handleDashboardClick()
                        setIsMenuOpen(false)
                      }}
                      className="text-left text-brand-600 hover:text-brand-700 font-medium transition-colors"
                    >
                      Dashboard
                    </button>
                    <button
                      onClick={() => {
                        handleSignOut()
                        setIsMenuOpen(false)
                      }}
                      className="text-left text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              ) : showGetStarted && onGetStarted ? (
                <div className="pt-4 border-t border-gray-100">
                  <button 
                    onClick={() => {
                      onGetStarted()
                      setIsMenuOpen(false)
                    }}
                    className="w-full btn-primary"
                  >
                    Get Started
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}