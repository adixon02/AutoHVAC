'use client';

import React, { useState, useEffect } from 'react';
import { Input, Select, Button, Card, CardHeader, CardTitle, CardContent, Alert } from '@/components/ui';
import { ClimateService } from '@/lib/climate-service';

export interface ProjectData {
  projectName: string;
  zipCode: string;
  buildingType: 'residential' | 'commercial';
  constructionType: 'new' | 'retrofit';
  inputMethod: 'blueprint' | 'manual';
}

export interface ProjectFormProps {
  initialData?: Partial<ProjectData>;
  onSubmit: (data: ProjectData) => void;
  onBack?: () => void;
  loading?: boolean;
}

const buildingTypeOptions = [
  { value: 'residential', label: 'Residential' },
  { value: 'commercial', label: 'Commercial' },
];

const constructionTypeOptions = [
  { value: 'new', label: 'New Construction' },
  { value: 'retrofit', label: 'Retrofit/Renovation' },
];

const ProjectForm: React.FC<ProjectFormProps> = ({
  initialData = {},
  onSubmit,
  onBack,
  loading = false
}) => {
  const [formData, setFormData] = useState<ProjectData>({
    projectName: initialData.projectName || '',
    zipCode: initialData.zipCode || '',
    buildingType: initialData.buildingType || 'residential',
    constructionType: initialData.constructionType || 'new',
    inputMethod: initialData.inputMethod || 'blueprint', // Default to blueprint!
  });

  const [errors, setErrors] = useState<Partial<Record<keyof ProjectData, string>>>({});
  const [zipValidation, setZipValidation] = useState<{
    loading: boolean;
    valid: boolean | null;
    climateZone?: string;
    error?: string;
  }>({ loading: false, valid: null });

  // Validate ZIP code when it changes
  useEffect(() => {
    const validateZipCode = async () => {
      if (formData.zipCode.length === 5 && /^\d{5}$/.test(formData.zipCode)) {
        setZipValidation({ loading: true, valid: null });
        
        try {
          const climateData = await ClimateService.getClimateData(formData.zipCode);
          setZipValidation({
            loading: false,
            valid: true,
            climateZone: climateData.zone,
          });
        } catch (error) {
          setZipValidation({
            loading: false,
            valid: false,
            error: error instanceof Error ? error.message : 'Invalid ZIP code',
          });
        }
      } else if (formData.zipCode.length > 0) {
        setZipValidation({
          loading: false,
          valid: false,
          error: 'ZIP code must be 5 digits',
        });
      } else {
        setZipValidation({ loading: false, valid: null });
      }
    };

    const timeoutId = setTimeout(validateZipCode, 300); // Debounce
    return () => clearTimeout(timeoutId);
  }, [formData.zipCode]);

  const handleInputChange = (field: keyof ProjectData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof ProjectData, string>> = {};

    if (!formData.projectName.trim()) {
      newErrors.projectName = 'Project name is required';
    } else if (formData.projectName.length < 3) {
      newErrors.projectName = 'Project name must be at least 3 characters';
    }

    if (!formData.zipCode.trim()) {
      newErrors.zipCode = 'ZIP code is required';
    } else if (!/^\d{5}$/.test(formData.zipCode)) {
      newErrors.zipCode = 'ZIP code must be 5 digits';
    } else if (zipValidation.valid === false) {
      newErrors.zipCode = zipValidation.error || 'Invalid ZIP code';
    }

    if (!formData.buildingType) {
      newErrors.buildingType = 'Building type is required';
    }

    if (!formData.constructionType) {
      newErrors.constructionType = 'Construction type is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm() && zipValidation.valid !== false) {
      onSubmit(formData);
    }
  };

  const isFormValid = formData.projectName.length >= 3 && 
                     formData.zipCode.length === 5 && 
                     zipValidation.valid === true &&
                     formData.buildingType && 
                     formData.constructionType;

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Project Setup</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Project Name */}
          <Input
            label="Project Name"
            name="projectName"
            value={formData.projectName}
            onChange={(e) => handleInputChange('projectName', e.target.value)}
            placeholder="e.g., Smith Residence, Office Building A"
            error={errors.projectName}
            required
          />

          {/* ZIP Code with validation */}
          <div>
            <Input
              label="ZIP Code"
              name="zipCode"
              value={formData.zipCode}
              onChange={(e) => handleInputChange('zipCode', e.target.value)}
              placeholder="12345"
              error={errors.zipCode}
              helperText="Used to determine climate zone for calculations"
              required
            />
            
            {zipValidation.loading && (
              <div className="mt-2 text-sm text-gray-500">
                Validating ZIP code...
              </div>
            )}
            
            {zipValidation.valid === true && zipValidation.climateZone && (
              <Alert variant="success" className="mt-2">
                Climate Zone: {zipValidation.climateZone} ({ClimateService.getClimateZoneDescription(zipValidation.climateZone)})
              </Alert>
            )}
          </div>

          {/* Building Type */}
          <Select
            label="Building Type"
            name="buildingType"
            value={formData.buildingType}
            onChange={(e) => handleInputChange('buildingType', e.target.value as 'residential' | 'commercial')}
            options={buildingTypeOptions}
            error={errors.buildingType}
            required
          />

          {/* Construction Type */}
          <Select
            label="Construction Type"
            name="constructionType"
            value={formData.constructionType}
            onChange={(e) => handleInputChange('constructionType', e.target.value as 'new' | 'retrofit')}
            options={constructionTypeOptions}
            error={errors.constructionType}
            required
          />

          {/* Input Method Selection - Emphasize Blueprint */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              How would you like to provide building details?
            </label>
            
            <div className="space-y-3">
              {/* Blueprint Upload - Primary Option */}
              <div
                className={`relative rounded-lg border-2 p-4 cursor-pointer transition-all ${
                  formData.inputMethod === 'blueprint'
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleInputChange('inputMethod', 'blueprint')}
              >
                <div className="flex items-start">
                  <input
                    type="radio"
                    name="inputMethod"
                    value="blueprint"
                    checked={formData.inputMethod === 'blueprint'}
                    onChange={() => handleInputChange('inputMethod', 'blueprint')}
                    className="mt-1 h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                  />
                  <div className="ml-3 flex-1">
                    <div className="flex items-center">
                      <h3 className="text-lg font-medium text-gray-900">
                        📄 Upload Blueprint (Recommended)
                      </h3>
                      <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Fast & Accurate
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      Upload your architectural drawings and we'll automatically extract room dimensions, 
                      areas, and building details using AI. Most accurate and fastest option.
                    </p>
                    <div className="mt-2 text-xs text-gray-400">
                      ✓ PDF format supported • ✓ Multiple pages • ✓ Up to 100MB
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Manual Entry - Secondary Option */}
              <div
                className={`relative rounded-lg border-2 p-4 cursor-pointer transition-all ${
                  formData.inputMethod === 'manual'
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleInputChange('inputMethod', 'manual')}
              >
                <div className="flex items-start">
                  <input
                    type="radio"
                    name="inputMethod"
                    value="manual"
                    checked={formData.inputMethod === 'manual'}
                    onChange={() => handleInputChange('inputMethod', 'manual')}
                    className="mt-1 h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                  />
                  <div className="ml-3 flex-1">
                    <h3 className="text-lg font-medium text-gray-900">
                      ✏️ Manual Entry
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                      Enter building and room details by hand. Takes longer but gives you 
                      complete control over all inputs.
                    </p>
                    <div className="mt-2 text-xs text-gray-400">
                      ⚠️ More time-consuming • ✓ Full control over inputs
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex justify-between pt-6">
            {onBack ? (
              <Button
                type="button"
                variant="outline"
                onClick={onBack}
                disabled={loading}
              >
                Back
              </Button>
            ) : (
              <div /> // Spacer
            )}
            
            <Button
              type="submit"
              loading={loading}
              disabled={!isFormValid || zipValidation.loading}
            >
              {formData.inputMethod === 'blueprint' ? 'Continue to Blueprint Upload' : 'Continue to Manual Entry'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export { ProjectForm };