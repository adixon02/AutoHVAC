import React, { memo } from 'react'
import { ProjectData } from './index'

interface Step3Props {
  projectData: ProjectData
  updateProjectData: (updates: Partial<ProjectData>) => void
  onNext: () => void
  onPrev: () => void
}

function Step3DuctConfig({ projectData, updateProjectData, onNext, onPrev }: Step3Props) {
  const ductOptions = [
    { 
      value: 'ducted_attic', 
      label: 'Ducted – Attic', 
      description: 'Traditional ductwork installed in attic space',
      icon: '🏠'
    },
    { 
      value: 'ducted_crawl', 
      label: 'Ducted – Crawl Space', 
      description: 'Traditional ductwork installed in crawl space',
      icon: '🏗️'
    },
    { 
      value: 'ductless', 
      label: 'Ductless / Mini-split', 
      description: 'Individual room units with no central ductwork',
      icon: '❄️'
    }
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {ductOptions.map((option) => (
          <label 
            key={option.value}
            className={`flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${
              projectData.ductConfig === option.value 
                ? 'border-brand-500 bg-brand-50' 
                : 'border-gray-200 hover:border-brand-300'
            }`}
          >
            <input
              type="radio"
              name="duct_config"
              value={option.value}
              checked={projectData.ductConfig === option.value}
              onChange={(e) => updateProjectData({ ductConfig: e.target.value as any })}
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
          Next: Heating System
        </button>
      </div>
    </div>
  )
}

export default memo(Step3DuctConfig)