import React, { memo } from 'react'
import { ProjectData } from './index'

interface Step4Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onNext: () => void
  onPrev: () => void
}

function Step4HeatingSystem({ projectData, updateProjectData, onNext, onPrev }: Step4Props) {
  const heatingOptions = [
    { 
      value: 'gas', 
      label: 'Natural Gas Furnace', 
      description: 'Traditional gas-fired heating system',
      icon: '🔥'
    },
    { 
      value: 'heat_pump', 
      label: 'Heat Pump', 
      description: 'Electric heat pump for both heating and cooling',
      icon: '⚡'
    },
    { 
      value: 'electric', 
      label: 'Electric Resistance', 
      description: 'Electric baseboard or forced air heating',
      icon: '🔌'
    }
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {heatingOptions.map((option) => (
          <label 
            key={option.value}
            className={`flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${
              projectData.heatingFuel === option.value 
                ? 'border-brand-500 bg-brand-50' 
                : 'border-gray-200 hover:border-brand-300'
            }`}
          >
            <input
              type="radio"
              name="heating_fuel"
              value={option.value}
              checked={projectData.heatingFuel === option.value}
              onChange={(e) => updateProjectData({ heatingFuel: e.target.value as any })}
              className="w-5 h-5 text-brand-600 mt-0.5 mr-4"
            />
            <div className="text-2xl mr-4">{option.icon}</div>
            <div>
              <div className="font-medium text-gray-900">{option.label}</div>
              <div className="text-sm text-gray-600 mt-1">{option.description}</div>
            </div>
          </label>
        ))}
      </div>

      <div className="flex space-x-4">
        <button onClick={onPrev} className="flex-1 btn-secondary text-lg py-4">
          Back
        </button>
        <button onClick={onNext} className="flex-1 btn-primary text-lg py-4">
          Next: Project Location
        </button>
      </div>
    </div>
  )
}

export default memo(Step4HeatingSystem)