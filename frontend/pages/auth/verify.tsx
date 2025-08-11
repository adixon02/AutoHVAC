import Head from 'next/head'
import { useRouter } from 'next/router'

export default function VerifyRequest() {
  const router = useRouter()
  
  return (
    <>
      <Head>
        <title>Check your email - AutoHVAC</title>
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-25 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="card glass p-8 text-center">
            <div className="w-16 h-16 bg-brand-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            
            <h1 className="display-xs text-gray-900 mb-2">
              Check your email
            </h1>
            
            <p className="text-gray-600 mb-6">
              A sign in link has been sent to your email address.
            </p>
            
            <div className="bg-gray-50 rounded-xl p-4 mb-6">
              <p className="text-sm text-gray-700">
                <strong>Tip:</strong> The email might take a minute to arrive. 
                Check your spam folder if you don't see it.
              </p>
            </div>
            
            <button
              onClick={() => router.push('/')}
              className="btn-text"
            >
              ← Back to home
            </button>
          </div>
        </div>
      </div>
    </>
  )
}