import React, { useState } from 'react'

interface AssumptionValues {
  duct_config: 'ducted_attic' | 'ducted_crawl' | 'ductless' | ''
  heating_fuel: 'gas' | 'heat_pump' | 'electric' | ''
}

interface AssumptionModalProps {
  isOpen: boolean
  onSubmit: (values: AssumptionValues) => void
  onClose: () => void
  isLoading?: boolean
}

export default function AssumptionModal({ isOpen, onSubmit, onClose, isLoading = false }: AssumptionModalProps) {
  const [values, setValues] = useState<AssumptionValues>({
    duct_config: 'ducted_attic',  // Pre-select most common option
    heating_fuel: 'gas'           // Pre-select most common option
  })
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = () => {
    if (!values.duct_config || !values.heating_fuel) {
      setError('Please select both duct configuration and heating fuel type')
      return
    }
    
    setError(null)
    onSubmit(values)
  }

  const handleDuctConfigChange = (value: AssumptionValues['duct_config']) => {
    setValues(prev => ({ ...prev, duct_config: value }))
    setError(null)
  }

  const handleHeatingFuelChange = (value: AssumptionValues['heating_fuel']) => {
    setValues(prev => ({ ...prev, heating_fuel: value }))
    setError(null)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h2 className="text-2xl font-semibold text-brand-700">
            Manual J Assumptions
          </h2>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8">
          <div className="text-center">
            <p className="text-gray-600">
              To complete your Manual J load calculation, we need a couple of assumptions about your HVAC system configuration.
            </p>
          </div>

          {/* Duct Configuration */}
          <div>
            <h3 className="text-lg font-medium text-brand-700 mb-4">Duct Configuration</h3>
            <div className="space-y-3">
              {[
                { value: 'ducted_attic', label: 'Ducted – Attic', description: 'Traditional ductwork installed in attic space' },
                { value: 'ducted_crawl', label: 'Ducted – Crawl Space', description: 'Traditional ductwork installed in crawl space' },
                { value: 'ductless', label: 'Ductless / Mini-split', description: 'Individual room units with no central ductwork' }
              ].map((option) => (
                <label 
                  key={option.value}
                  className={`flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${
                    values.duct_config === option.value 
                      ? 'border-brand-500 bg-brand-50' 
                      : 'border-gray-200 hover:border-brand-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="duct_config"
                    value={option.value}
                    checked={values.duct_config === option.value}
                    onChange={(e) => handleDuctConfigChange(e.target.value as AssumptionValues['duct_config'])}
                    className="w-5 h-5 text-brand-600 mt-0.5 mr-4"
                    disabled={isLoading}
                  />
                  <div>
                    <div className="font-medium text-gray-900">{option.label}</div>
                    <div className="text-sm text-gray-600 mt-1">{option.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Heating Fuel */}
          <div>
            <h3 className="text-lg font-medium text-brand-700 mb-4">Heating Fuel Type</h3>
            <div className="space-y-3">
              {[
                { value: 'gas', label: 'Natural Gas Furnace', description: 'Traditional gas-fired heating system' },
                { value: 'heat_pump', label: 'Heat Pump', description: 'Electric heat pump for both heating and cooling' },
                { value: 'electric', label: 'Electric Resistance', description: 'Electric baseboard or forced air heating' }
              ].map((option) => (
                <label 
                  key={option.value}
                  className={`flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${
                    values.heating_fuel === option.value 
                      ? 'border-brand-500 bg-brand-50' 
                      : 'border-gray-200 hover:border-brand-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="heating_fuel"
                    value={option.value}
                    checked={values.heating_fuel === option.value}
                    onChange={(e) => handleHeatingFuelChange(e.target.value as AssumptionValues['heating_fuel'])}
                    className="w-5 h-5 text-brand-600 mt-0.5 mr-4"
                    disabled={isLoading}
                  />
                  <div>
                    <div className="font-medium text-gray-900">{option.label}</div>
                    <div className="text-sm text-gray-600 mt-1">{option.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-red-800 mb-1">Please Complete Selection</h4>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="w-full btn-primary text-lg py-4 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Continuing Analysis...
              </div>
            ) : (
              'Continue Analysis'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}