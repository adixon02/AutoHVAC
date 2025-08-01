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
    heating_total: number
    cooling_total: number
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
}

export default function ResultsPreview({ result, userEmail, onCreateAccount }: ResultsPreviewProps) {
  const router = useRouter()
  
  // Calculate tons from BTU
  const heatingTons = (result.heating_total / 12000).toFixed(1)
  const coolingTons = (result.cooling_total / 12000).toFixed(1)
  
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
                {result.heating_total.toLocaleString()} 
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
                {result.cooling_total.toLocaleString()}
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

      {/* Room Breakdown */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Room-by-Room Breakdown</h3>
        <div className="space-y-2">
          {result.zones.slice(0, 5).map((zone, index) => (
            <div key={index} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
              <div>
                <p className="font-medium text-gray-900">{zone.name}</p>
                <p className="text-sm text-gray-500">{zone.area} sq ft</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">
                  <span className="text-blue-600">{zone.heating_btu.toLocaleString()}</span> / 
                  <span className="text-cyan-600"> {zone.cooling_btu.toLocaleString()}</span> BTU/hr
                </p>
              </div>
            </div>
          ))}
          {result.zones.length > 5 && (
            <p className="text-sm text-gray-500 pt-2">+ {result.zones.length - 5} more rooms</p>
          )}
        </div>
      </div>

      {/* Equipment Recommendations */}
      {result.equipment_recommendations && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-amber-900 mb-3">Recommended Equipment Size</h3>
          <div className="space-y-2 text-amber-800">
            {result.equipment_recommendations.heating_size_tons && (
              <p>
                <strong>Heating:</strong> {result.equipment_recommendations.heating_size_tons} ton system
              </p>
            )}
            {result.equipment_recommendations.cooling_size_tons && (
              <p>
                <strong>Cooling:</strong> {result.equipment_recommendations.cooling_size_tons} ton system
              </p>
            )}
            {result.equipment_recommendations.system_type && (
              <p>
                <strong>Type:</strong> {result.equipment_recommendations.system_type}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Save Results CTA */}
      {userEmail && !onCreateAccount && (
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