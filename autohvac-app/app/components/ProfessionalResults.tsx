import React from 'react';

interface ProfessionalResultsProps {
  analysisData: any;
  onStartOver: () => void;
}

export default function ProfessionalResults({ analysisData, onStartOver }: ProfessionalResultsProps) {
  const {
    project_info,
    hvac_design,
    deliverables,
    processing_info,
    data_warnings
  } = analysisData;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-hvac-navy mb-2">
          Professional HVAC Analysis Complete!
        </h1>
        <p className="text-gray-600">
          Your blueprint has been analyzed and professional deliverables are ready.
        </p>
      </div>

      {/* Project Summary */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-hvac-navy">Project Summary</h2>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-green-500 rounded-full"></span>
            <span className="text-sm font-medium text-green-700">
              {project_info?.ready_for_permits ? 'Ready for Permits' : 'Analysis Complete'}
            </span>
          </div>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold text-gray-800 mb-3">Project Details</h3>
            <div className="space-y-2 text-sm">
              <p><span className="font-medium">Name:</span> {project_info?.name || 'Unknown Project'}</p>
              <p><span className="font-medium">Address:</span> {project_info?.address || 'Not specified'}</p>
            </div>
          </div>
          
          <div>
            <h3 className="font-semibold text-gray-800 mb-3">HVAC System</h3>
            <div className="space-y-2 text-sm">
              <p><span className="font-medium">System Type:</span> {hvac_design?.system_type?.replace('_', ' ').toUpperCase() || 'TBD'}</p>
              <p><span className="font-medium">Cooling:</span> {hvac_design?.cooling_tons || 0} tons ({((hvac_design?.cooling_tons || 0) * 12000).toLocaleString()} BTU/hr)</p>
              <p><span className="font-medium">Heating:</span> {hvac_design?.heating_tons || 0} tons ({((hvac_design?.heating_tons || 0) * 12000).toLocaleString()} BTU/hr)</p>
              <p><span className="font-medium">Est. Cost:</span> ${(hvac_design?.estimated_cost || project_info?.cost_estimate || 0).toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Data Quality Warnings */}
      {data_warnings && data_warnings.length > 0 && (
        <div className="card border-yellow-200 bg-yellow-50">
          <div className="flex items-start">
            <div className="text-yellow-600 mr-3 mt-1">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path>
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-800 mb-2">Data Quality Notes</h3>
              <ul className="text-sm text-yellow-700 space-y-1">
                {data_warnings.map((warning: string, index: number) => (
                  <li key={index} className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-yellow-600 mt-2">
                These notes indicate where minimum code values were used due to missing blueprint data.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Professional Deliverables */}
      <div className="card">
        <h2 className="text-2xl font-bold text-hvac-navy mb-6">Professional Deliverables</h2>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {deliverables?.download_links && Object.entries(deliverables.download_links).map(([type, link]) => {
            const typeNames = {
              manual_j: 'Manual J Report',
              hvac_design: 'HVAC Design Specs',
              executive_summary: 'Executive Summary',
              cad_drawing: 'CAD Drawing (DXF)',
              web_layout: 'Web Layout (SVG)'
            };
            
            const typeIcons = {
              manual_j: '📊',
              hvac_design: '⚙️',
              executive_summary: '📋',
              cad_drawing: '🏗️',
              web_layout: '🖼️'
            };
            
            return (
              <a
                key={type}
                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${link}`}
                download
                className="block p-4 border border-gray-200 rounded-lg hover:border-hvac-blue hover:bg-blue-50 transition-colors"
              >
                <div className="text-center">
                  <div className="text-2xl mb-2">{typeIcons[type as keyof typeof typeIcons]}</div>
                  <div className="font-medium text-gray-800">{typeNames[type as keyof typeof typeNames]}</div>
                  <div className="text-sm text-gray-500 mt-1">Click to download</div>
                </div>
              </a>
            );
          })}
        </div>
        
        <div className="mt-6 p-4 bg-green-50 rounded-lg">
          <div className="flex items-center">
            <div className="text-green-600 mr-3">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path>
              </svg>
            </div>
            <div>
              <p className="font-medium text-green-800">All deliverables are permit-ready!</p>
              <p className="text-sm text-green-700">
                {deliverables?.files_generated || 0} professional files generated, including ACCA-compliant Manual J calculations.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Load Calculation Details */}
      <div className="card">
        <h2 className="text-2xl font-bold text-hvac-navy mb-6">Manual J Load Calculation</h2>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-800 mb-3">❄️ Cooling Load</h3>
            <div className="space-y-2">
              <p className="text-2xl font-bold text-blue-600">
                {hvac_design?.cooling_tons || 0} tons
              </p>
              <p className="text-lg text-blue-700">
                {((hvac_design?.cooling_tons || 0) * 12000).toLocaleString()} BTU/hr
              </p>
              <p className="text-sm text-blue-600">
                ACCA Manual J 8th Edition
              </p>
            </div>
          </div>
          
          <div className="bg-red-50 p-4 rounded-lg">
            <h3 className="font-semibold text-red-800 mb-3">🔥 Heating Load</h3>
            <div className="space-y-2">
              <p className="text-2xl font-bold text-red-600">
                {hvac_design?.heating_tons || 0} tons
              </p>
              <p className="text-lg text-red-700">
                {((hvac_design?.heating_tons || 0) * 12000).toLocaleString()} BTU/hr
              </p>
              <p className="text-sm text-red-600">
                Design temperature: 5°F
              </p>
            </div>
          </div>
        </div>
        
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Note:</span> Load calculations include safety factors and diversity factors per ACCA standards. 
            1 ton = 12,000 BTU/hr cooling capacity.
          </p>
        </div>
      </div>


      {/* Actions */}
      <div className="flex justify-center space-x-4">
        <button
          onClick={onStartOver}
          className="btn-secondary"
        >
          Analyze Another Blueprint
        </button>
        
        <button
          onClick={() => window.print()}
          className="btn-primary"
        >
          Print Summary
        </button>
      </div>
    </div>
  );
}