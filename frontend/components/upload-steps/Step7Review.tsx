import React, { memo } from 'react'
import { ProjectData } from './index'

interface Step7Props {
  projectData: ProjectData
  onNext: () => void
  onPrev: () => void
}

function Step7Review({ projectData, onNext, onPrev }: Step7Props) {
  return (
    <div className="space-y-6">
      <div className="bg-gray-50 rounded-xl p-6 space-y-4">
        <h3 className="font-medium text-brand-700 mb-4">Review Your Project Details</h3>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Project Name</span>
            <span className="text-sm font-medium text-gray-900">{projectData.projectName}</span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Blueprint File</span>
            <span className="text-sm font-medium text-gray-900">{projectData.blueprintFile?.name}</span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Square Footage</span>
            <span className="text-sm font-medium text-gray-900">{projectData.squareFootage ? `${projectData.squareFootage} sq ft` : 'Not specified'}</span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Number of Stories</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.numberOfStories === '1' && '1 Story'}
              {projectData.numberOfStories === '2' && '2 Stories'}
              {projectData.numberOfStories === '3+' && '3+ Stories'}
              {!projectData.numberOfStories && 'Not specified'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Duct Configuration</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.ductConfig === 'ducted_attic' && 'Ducted – Attic'}
              {projectData.ductConfig === 'ducted_crawl' && 'Ducted – Crawl Space'}
              {projectData.ductConfig === 'ductless' && 'Ductless / Mini-split'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">Heating System</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.heatingFuel === 'gas' && 'Natural Gas Furnace'}
              {projectData.heatingFuel === 'heat_pump' && 'Heat Pump'}
              {projectData.heatingFuel === 'electric' && 'Electric Resistance'}
            </span>
          </div>
          
          <div className="flex justify-between items-center py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">ZIP Code</span>
            <span className="text-sm font-medium text-gray-900">{projectData.zipCode}</span>
          </div>
          
          <div className="flex justify-between items-center py-2">
            <span className="text-sm text-gray-600">Building Orientation</span>
            <span className="text-sm font-medium text-gray-900">
              {projectData.buildingOrientation === 'N' && 'North'}
              {projectData.buildingOrientation === 'NE' && 'Northeast'}
              {projectData.buildingOrientation === 'E' && 'East'}
              {projectData.buildingOrientation === 'SE' && 'Southeast'}
              {projectData.buildingOrientation === 'S' && 'South'}
              {projectData.buildingOrientation === 'SW' && 'Southwest'}
              {projectData.buildingOrientation === 'W' && 'West'}
              {projectData.buildingOrientation === 'NW' && 'Northwest'}
              {projectData.buildingOrientation === 'unknown' && '🧭 Not sure (will estimate)'}
              {!projectData.buildingOrientation && 'Not specified'}
            </span>
          </div>
        </div>
      </div>

      <div className="bg-brand-50 border border-brand-200 rounded-xl p-4">
        <p className="text-sm text-brand-800">
          <strong>Next step:</strong> Enter your email to receive your comprehensive HVAC analysis report.
        </p>
      </div>

      <div className="flex space-x-4">
        <button onClick={onPrev} className="flex-1 btn-secondary text-lg py-4">
          Back
        </button>
        <button onClick={onNext} className="flex-1 btn-primary text-lg py-4">
          Continue to Final Step
        </button>
      </div>
    </div>
  )
}

export default memo(Step7Review)