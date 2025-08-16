import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { useSession, signOut } from 'next-auth/react'

interface NavBarProps {
  onGetStarted?: () => void
  showGetStarted?: boolean
}

export default function NavBar({ onGetStarted, showGetStarted = true }: NavBarProps) {
  const router = useRouter()
  const { data: session } = useSession()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    // Handle scroll effect
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleSignOut = () => {
    signOut({ callbackUrl: '/' })
  }

  const handleDashboardClick = () => {
    router.push('/dashboard')
  }

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
      isScrolled 
        ? 'bg-white/70 backdrop-blur-xl border-b border-gray-200/50 shadow-sm' 
        : 'bg-white/50 backdrop-blur-md border-b border-gray-100/50'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2 group">
              <div className="w-8 h-8 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center shadow-sm group-hover:shadow-md transition-all duration-200">
                <span className="text-white font-bold text-sm">AH</span>
              </div>
              <span className="text-xl font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                AutoHVAC
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {/* Navigation Links */}
            <div className="flex items-center space-x-8">
              <Link href="/blog" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Blog
              </Link>
            </div>

            {/* User Section */}
            {session?.user?.email ? (
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleDashboardClick}
                  className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-50 transition-all"
                >
                  Dashboard
                </button>
                <div className="relative group">
                  <button className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-all">
                    <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-600 rounded-full flex items-center justify-center text-white text-xs font-medium shadow-sm">
                      {session?.user?.email.charAt(0).toUpperCase()}
                    </div>
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 border border-gray-100">
                    <div className="px-4 py-2 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900 truncate">{session?.user?.email}</p>
                    </div>
                    <button
                      onClick={handleSignOut}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link href="/signin" className="text-sm font-medium text-gray-700 hover:text-gray-900 px-4 py-2">
                  Sign In
                </Link>
                {showGetStarted && onGetStarted && (
                  <button
                    onClick={onGetStarted}
                    className="btn-primary"
                  >
                    Get Started
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="btn-icon"
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
          <div className="md:hidden border-t border-gray-100 py-4 animate-slide-down">
            <div className="flex flex-col space-y-1">
              {/* Navigation Links */}
              <Link 
                href="/blog" 
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-all"
                onClick={() => setIsMenuOpen(false)}
              >
                Blog
              </Link>

              {/* User Section */}
              {session?.user?.email ? (
                <div className="pt-4 border-t border-gray-100">
                  <div className="text-sm text-gray-600 mb-2 truncate">
                    Signed in as: {session?.user?.email}
                  </div>
                  <div className="flex flex-col space-y-2">
                    <button
                      onClick={() => {
                        handleDashboardClick()
                        setIsMenuOpen(false)
                      }}
                      className="btn-text text-left"
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