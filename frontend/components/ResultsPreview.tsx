import React from 'react'
import { useRouter } from 'next/router'

interface Zone {
  name: string
  area: number
  heating_btu: number
  cooling_btu: number
  room_type?: string
}

interface ResultsPreviewProps {
  result: {
    heating_load_btu_hr: number
    cooling_load_btu_hr: number
    zones: Zone[]
    climate_zone?: string
    equipment_recommendations?: {
      heating_size_tons?: number
      cooling_size_tons?: number
      system_type?: string
    }
  }
  userEmail?: string | null
  onCreateAccount?: () => void
  isLoggedIn?: boolean
}

export default function ResultsPreview({ result, userEmail, onCreateAccount, isLoggedIn }: ResultsPreviewProps) {
  const router = useRouter()
  
  // Calculate tons from BTU
  const heatingTons = (result.heating_load_btu_hr / 12000).toFixed(1)
  const coolingTons = (result.cooling_load_btu_hr / 12000).toFixed(1)
  
  return (
    <div className="space-y-6">
      {/* Success Message */}
      <div className="text-center mb-8">
        <div className="w-20 h-20 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
          <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Your HVAC Analysis is Ready!</h2>
        <p className="text-gray-600">Here's what we found for your building</p>
      </div>

      {/* Key Results Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-blue-700">Total Heating Load</p>
              <p className="text-3xl font-bold text-blue-900 mt-1">
                {result.heating_load_btu_hr.toLocaleString()} 
                <span className="text-lg font-normal text-blue-700"> BTU/hr</span>
              </p>
              <p className="text-sm text-blue-600 mt-1">≈ {heatingTons} tons</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-lg">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14v6m-3-3h6M6 10h2a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2zm10 0h2a2 2 0 002-2V6a2 2 0 00-2-2h-2a2 2 0 00-2 2v2a2 2 0 002 2zM6 20h2a2 2 0 002-2v-2a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-cyan-50 border border-cyan-200 rounded-xl p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-cyan-700">Total Cooling Load</p>
              <p className="text-3xl font-bold text-cyan-900 mt-1">
                {result.cooling_load_btu_hr.toLocaleString()}
                <span className="text-lg font-normal text-cyan-700"> BTU/hr</span>
              </p>
              <p className="text-sm text-cyan-600 mt-1">≈ {coolingTons} tons</p>
            </div>
            <div className="p-3 bg-cyan-100 rounded-lg">
              <svg className="w-6 h-6 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* AI-Generated Equipment Recommendations */}
      {result.equipment_recommendations && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
          <div className="flex items-center mb-4">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a9 9 0 111.414-1.414l-1.414 1.414z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-blue-900">Professional Equipment Recommendations</h3>
              <p className="text-sm text-blue-600">AI-powered analysis based on your Manual J calculations</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* System Type Recommendation */}
            {result.equipment_recommendations.system_type_recommendation && (
              <div className="bg-white bg-opacity-60 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Recommended System Type
                </h4>
                <p className="text-blue-800 text-sm">{result.equipment_recommendations.system_type_recommendation}</p>
              </div>
            )}

            {/* Equipment Sizing */}
            {result.equipment_recommendations.equipment_sizing && (
              <div className="bg-white bg-opacity-60 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  Equipment Sizing
                </h4>
                <p className="text-blue-800 text-sm">{result.equipment_recommendations.equipment_sizing}</p>
              </div>
            )}

            {/* Efficiency Recommendations */}
            {result.equipment_recommendations.efficiency_recommendations && (
              <div className="bg-white bg-opacity-60 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  Efficiency Standards
                </h4>
                <p className="text-blue-800 text-sm">{result.equipment_recommendations.efficiency_recommendations}</p>
              </div>
            )}

            {/* Regional Factors */}
            {result.equipment_recommendations.regional_factors && (
              <div className="bg-white bg-opacity-60 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Climate Considerations
                </h4>
                <p className="text-blue-800 text-sm">{result.equipment_recommendations.regional_factors}</p>
              </div>
            )}
          </div>

          {/* Installation Considerations */}
          {result.equipment_recommendations.installation_considerations && (
            <div className="mt-4 bg-white bg-opacity-60 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                </svg>
                Installation Considerations
              </h4>
              <p className="text-blue-800 text-sm">{result.equipment_recommendations.installation_considerations}</p>
            </div>
          )}

          {/* Cost Considerations */}
          {result.equipment_recommendations.cost_considerations && (
            <div className="mt-4 bg-white bg-opacity-60 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
                Cost Considerations
              </h4>
              <p className="text-blue-800 text-sm">{result.equipment_recommendations.cost_considerations}</p>
            </div>
          )}

          {/* Contractor Notes */}
          {result.equipment_recommendations.contractor_notes && (
            <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h4 className="font-semibold text-amber-900 mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                For HVAC Contractors
              </h4>
              <p className="text-amber-800 text-sm">{result.equipment_recommendations.contractor_notes}</p>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between text-xs text-blue-600">
            <div className="flex items-center">
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Generated by AI based on ACCA Manual J calculations
            </div>
          </div>
        </div>
      )}

      {/* Save Results CTA */}
      {userEmail && !onCreateAccount && !isLoggedIn && (
        <div className="bg-brand-50 border border-brand-200 rounded-xl p-6 text-center">
          <h3 className="text-lg font-semibold text-brand-900 mb-2">Want to save these results?</h3>
          <p className="text-brand-700 mb-4">
            Create a free account to download the full report, share with contractors, and track multiple projects.
          </p>
          <button 
            onClick={() => router.push(`/auth/signin?callbackUrl=/dashboard&email=${encodeURIComponent(userEmail)}`)}
            className="btn-primary"
          >
            Create Account & Save Results
          </button>
          <p className="text-sm text-brand-600 mt-3">
            We'll send a magic link to <strong>{userEmail}</strong>
          </p>
        </div>
      )}

      {/* What's Next */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">What's Next?</h3>
        <div className="space-y-3 text-gray-600">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Share these results with HVAC contractors for accurate quotes</p>
          </div>
          <div className="flex items-start">
            <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Use the load calculations to ensure properly sized equipment</p>
          </div>
          <div className="flex items-start">
            <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Consider both heating and cooling needs for your climate zone</p>
          </div>
        </div>
      </div>
    </div>
  )
}