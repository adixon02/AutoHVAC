import React, { memo } from 'react'
import { ProjectData } from './index'

interface Step6Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onNext: () => void
  onPrev: () => void
}

function Step6Orientation({ projectData, updateProjectData, onNext, onPrev }: Step6Props) {
  const orientations = [
    { value: 'N', label: 'North', icon: '⬆️' },
    { value: 'NE', label: 'Northeast', icon: '↗️' },
    { value: 'E', label: 'East', icon: '➡️' },
    { value: 'SE', label: 'Southeast', icon: '↘️' },
    { value: 'S', label: 'South', icon: '⬇️' },
    { value: 'SW', label: 'Southwest', icon: '↙️' },
    { value: 'W', label: 'West', icon: '⬅️' },
    { value: 'NW', label: 'Northwest', icon: '↖️' },
    { value: 'unknown', label: 'Not sure', icon: '🧭', subtitle: "We'll estimate for you" }
  ]

  const handleNext = () => {
    if (!projectData.buildingOrientation) {
      updateProjectData({ buildingOrientation: 'unknown' })
    }
    onNext()
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-gray-600 mb-6">
          Knowing your building's orientation helps us calculate accurate solar heat gains for each room, 
          improving system sizing by up to 20%.
        </p>
        
        <div className="grid grid-cols-2 gap-3">
          {orientations.slice(0, 8).map(orientation => (
            <button
              key={orientation.value}
              onClick={() => updateProjectData({ buildingOrientation: orientation.value as any })}
              className={`p-4 border-2 rounded-xl transition-all ${
                projectData.buildingOrientation === orientation.value 
                  ? 'border-brand-600 bg-brand-50 shadow-md' 
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-center">
                <span className="text-2xl mr-2">{orientation.icon}</span>
                <span className="font-medium">{orientation.label}</span>
              </div>
            </button>
          ))}
          
          <button
            onClick={() => updateProjectData({ buildingOrientation: 'unknown' })}
            className={`col-span-2 p-4 border-2 rounded-xl transition-all ${
              projectData.buildingOrientation === 'unknown' 
                ? 'border-brand-600 bg-brand-50 shadow-md' 
                : 'border-gray-200 hover:border-gray-300 bg-gray-50'
            }`}
          >
            <div className="flex flex-col items-center justify-center">
              <div className="flex items-center">
                <span className="text-2xl mr-2">{orientations[8].icon}</span>
                <span className="font-medium">{orientations[8].label}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{orientations[8].subtitle}</p>
            </div>
          </button>
        </div>
        
        <div className="mt-4 space-y-2">
          <p className="text-xs text-gray-500 text-center">
            Tip: Face the front door and note which compass direction you're looking at
          </p>
          <p className="text-xs text-gray-400 text-center">
            Selecting "Not sure" will use climate-based estimates, affecting accuracy by ~5-10%
          </p>
        </div>
      </div>

      <div className="flex space-x-4">
        <button onClick={onPrev} className="flex-1 btn-secondary text-lg py-4">
          Back
        </button>
        <button onClick={handleNext} className="flex-1 btn-primary text-lg py-4">
          Continue
        </button>
      </div>
    </div>
  )
}

export default memo(Step6Orientation)