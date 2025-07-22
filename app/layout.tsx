import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], display: 'swap' })

export const metadata: Metadata = {
  title: 'AutoHVAC AI - Smart HVAC Design in Minutes',
  description: 'Professional AI-powered HVAC system design and Manual J calculations for contractors and engineers',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* Premium AI SaaS Navigation */}
        <nav className="fixed top-0 w-full z-50 glass-strong shadow-soft backdrop-blur-2xl">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex justify-between items-center h-20">
              <div className="flex items-center space-x-8">
                {/* Logo */}
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-primary rounded-2xl flex items-center justify-center shadow-glow">
                    <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2L2 7v10c0 5.55 3.84 9.74 9 11 5.16-1.26 9-5.45 9-11V7l-10-5z"/>
                      <path d="M12 8v8m-4-4h8" stroke="white" strokeWidth="1.5" fill="none"/>
                    </svg>
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-industrial-900 to-primary-600 bg-clip-text text-transparent">
                      AutoHVAC
                    </h1>
                    <p className="text-xs text-industrial-500 font-medium -mt-1">AI-Powered</p>
                  </div>
                </div>

                {/* Navigation Links */}
                <div className="hidden md:flex items-center space-x-1">
                  <button className="btn-ghost text-sm">Dashboard</button>
                  <button className="btn-ghost text-sm">Projects</button>
                  <button className="btn-ghost text-sm">Reports</button>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                {/* Status Indicator */}
                <div className="status-online">
                  <div className="w-2 h-2 bg-accent-emerald rounded-full mr-2 animate-pulse"></div>
                  AI Ready
                </div>
                
                {/* Demo Badge */}
                <div className="hidden sm:flex status-processing">
                  <svg className="w-3 h-3 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                  MVP Demo
                </div>

                {/* User Avatar */}
                <div className="w-10 h-10 bg-gradient-to-br from-primary-400 to-accent-cyan rounded-2xl flex items-center justify-center shadow-medium">
                  <span className="text-white font-semibold text-sm">JD</span>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content with Premium Background */}
        <main className="min-h-screen pt-20">
          {/* Animated Background Elements */}
          <div className="fixed inset-0 overflow-hidden pointer-events-none">
            <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
            <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent-cyan rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse" style={{animationDelay: '2s'}}></div>
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-60 h-60 bg-accent-purple rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-pulse" style={{animationDelay: '4s'}}></div>
          </div>
          
          {/* Content Container */}
          <div className="relative z-10">
            {children}
          </div>
        </main>

        {/* Premium Footer */}
        <footer className="glass border-t border-white/20 mt-20">
          <div className="max-w-7xl mx-auto px-6 lg:px-8 py-12">
            <div className="text-center">
              <div className="flex items-center justify-center space-x-3 mb-4">
                <div className="w-8 h-8 bg-gradient-primary rounded-xl flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L2 7v10c0 5.55 3.84 9.74 9 11 5.16-1.26 9-5.45 9-11V7l-10-5z"/>
                  </svg>
                </div>
                <span className="text-industrial-700 font-semibold">AutoHVAC AI</span>
              </div>
              <p className="text-sm text-industrial-600 mb-4">
                Revolutionizing HVAC design with artificial intelligence
              </p>
              <div className="flex items-center justify-center space-x-6 text-xs text-industrial-500">
                <span>© 2025 AutoHVAC AI</span>
                <span>•</span>
                <span>Privacy Policy</span>
                <span>•</span>
                <span>Terms of Service</span>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  )
}