'use client';

import { useState } from 'react';
import { BuildingInfo, ProjectInfo } from '../lib/types';

interface BuildingInputProps {
  onSubmit: (data: BuildingInfo) => void;
  onBack: () => void;
  projectInfo: ProjectInfo;
}

export default function BuildingInput({ onSubmit, onBack, projectInfo }: BuildingInputProps) {
  const [formData, setFormData] = useState<BuildingInfo>({
    squareFootage: 2000,
    stories: 1,
    ceilingHeight: 9,
    foundationType: 'slab',
    insulationQuality: 'average',
    windowType: 'double',
    windowArea: 200,
    orientation: 'north'
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="card max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-hvac-navy">Building Details</h2>
        <p className="text-gray-600 mt-1">Project: {projectInfo.projectName}</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Total Square Footage
            </label>
            <input
              type="number"
              required
              min="500"
              max="50000"
              className="input-field"
              value={formData.squareFootage}
              onChange={(e) => setFormData({ ...formData, squareFootage: parseInt(e.target.value) })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Stories
            </label>
            <select
              className="input-field"
              value={formData.stories}
              onChange={(e) => setFormData({ ...formData, stories: parseInt(e.target.value) })}
            >
              <option value="1">1 Story</option>
              <option value="2">2 Stories</option>
              <option value="3">3 Stories</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Average Ceiling Height (ft)
            </label>
            <input
              type="number"
              required
              min="8"
              max="20"
              className="input-field"
              value={formData.ceilingHeight}
              onChange={(e) => setFormData({ ...formData, ceilingHeight: parseInt(e.target.value) })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Foundation Type
            </label>
            <select
              className="input-field"
              value={formData.foundationType}
              onChange={(e) => setFormData({ ...formData, foundationType: e.target.value as any })}
            >
              <option value="slab">Slab on Grade</option>
              <option value="crawlspace">Crawl Space</option>
              <option value="basement">Basement</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Insulation Quality
          </label>
          <div className="grid grid-cols-4 gap-3">
            {(['poor', 'average', 'good', 'excellent'] as const).map((quality) => (
              <button
                key={quality}
                type="button"
                className={`p-3 rounded-lg border-2 capitalize transition-all ${
                  formData.insulationQuality === quality 
                    ? 'border-hvac-blue bg-hvac-light' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onClick={() => setFormData({ ...formData, insulationQuality: quality })}
              >
                {quality}
              </button>
            ))}
          </div>
          <p className="mt-2 text-sm text-gray-600">
            Poor: R-7 walls, R-19 ceiling | Average: R-13 walls, R-30 ceiling | 
            Good: R-19 walls, R-38 ceiling | Excellent: R-30 walls, R-49 ceiling
          </p>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Window Type
            </label>
            <select
              className="input-field"
              value={formData.windowType}
              onChange={(e) => setFormData({ ...formData, windowType: e.target.value as any })}
            >
              <option value="single">Single Pane</option>
              <option value="double">Double Pane</option>
              <option value="triple">Triple Pane</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Total Window Area (sq ft)
            </label>
            <input
              type="number"
              required
              min="50"
              max="5000"
              className="input-field"
              value={formData.windowArea}
              onChange={(e) => setFormData({ ...formData, windowArea: parseInt(e.target.value) })}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Primary Building Orientation
          </label>
          <div className="grid grid-cols-4 gap-3">
            {(['north', 'south', 'east', 'west'] as const).map((dir) => (
              <button
                key={dir}
                type="button"
                className={`p-3 rounded-lg border-2 capitalize transition-all ${
                  formData.orientation === dir 
                    ? 'border-hvac-blue bg-hvac-light' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onClick={() => setFormData({ ...formData, orientation: dir })}
              >
                {dir}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-between pt-4">
          <button type="button" onClick={onBack} className="btn-secondary">
            Back
          </button>
          <button type="submit" className="btn-primary">
            Continue to Room Details
          </button>
        </div>
      </form>
    </div>
  );
}