'use client';

import { useState } from 'react';
import { ProjectInfo } from '../lib/types';

interface ProjectSetupProps {
  onSubmit: (data: ProjectInfo) => void;
}

export default function ProjectSetup({ onSubmit }: ProjectSetupProps) {
  const [formData, setFormData] = useState<ProjectInfo>({
    zipCode: '',
    projectName: '',
    projectType: 'residential',
    constructionType: 'new'
  });
  const [inputMethod, setInputMethod] = useState<'manual' | 'blueprint'>('blueprint');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ ...formData, inputMethod });
  };

  return (
    <div className="card max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-hvac-navy">Project Information</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Project Name
          </label>
          <input
            type="text"
            required
            className="input-field"
            value={formData.projectName}
            onChange={(e) => setFormData({ ...formData, projectName: e.target.value })}
            placeholder="e.g., Smith Residence"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ZIP Code
          </label>
          <input
            type="text"
            required
            pattern="[0-9]{5}"
            className="input-field"
            value={formData.zipCode}
            onChange={(e) => setFormData({ ...formData, zipCode: e.target.value })}
            placeholder="12345"
          />
          <p className="mt-1 text-sm text-gray-600">
            We'll use this to determine climate zone and local requirements
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Project Type
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              className={`p-4 rounded-lg border-2 transition-all ${
                formData.projectType === 'residential' 
                  ? 'border-hvac-blue bg-hvac-light' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => setFormData({ ...formData, projectType: 'residential' })}
            >
              <div className="font-semibold">Residential</div>
              <div className="text-sm text-gray-600">Single family homes</div>
            </button>
            <button
              type="button"
              className={`p-4 rounded-lg border-2 transition-all ${
                formData.projectType === 'commercial' 
                  ? 'border-hvac-blue bg-hvac-light' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => setFormData({ ...formData, projectType: 'commercial' })}
            >
              <div className="font-semibold">Commercial</div>
              <div className="text-sm text-gray-600">Office & retail spaces</div>
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Construction Type
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              className={`p-4 rounded-lg border-2 transition-all ${
                formData.constructionType === 'new' 
                  ? 'border-hvac-blue bg-hvac-light' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => setFormData({ ...formData, constructionType: 'new' })}
            >
              <div className="font-semibold">New Construction</div>
              <div className="text-sm text-gray-600">Building from scratch</div>
            </button>
            <button
              type="button"
              className={`p-4 rounded-lg border-2 transition-all ${
                formData.constructionType === 'retrofit' 
                  ? 'border-hvac-blue bg-hvac-light' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => setFormData({ ...formData, constructionType: 'retrofit' })}
            >
              <div className="font-semibold">Retrofit</div>
              <div className="text-sm text-gray-600">Replacing existing system</div>
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Input Method
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              className={`p-4 rounded-lg border-2 transition-all ${
                inputMethod === 'blueprint' 
                  ? 'border-hvac-blue bg-hvac-light' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => setInputMethod('blueprint')}
            >
              <div className="font-semibold">Upload Blueprint</div>
              <div className="text-sm text-gray-600">AI-powered blueprint analysis</div>
            </button>
            <button
              type="button"
              className={`p-4 rounded-lg border-2 transition-all ${
                inputMethod === 'manual' 
                  ? 'border-hvac-blue bg-hvac-light' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => setInputMethod('manual')}
            >
              <div className="font-semibold">Manual Input</div>
              <div className="text-sm text-gray-600">Enter room details manually</div>
            </button>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button type="submit" className="btn-primary">
            {inputMethod === 'blueprint' ? 'Continue to Blueprint Upload' : 'Continue to Building Details'}
          </button>
        </div>
      </form>
    </div>
  );
}