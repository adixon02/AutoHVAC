'use client';

import { useState } from 'react';
import { ProjectInfo } from '../lib/types';
import { Card, FormField, Input, SelectionGrid, Button } from './ui';

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
    <Card className="max-w-2xl mx-auto animate-fade-in" padding="lg" hover={true}>
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-neutral-900 mb-3">Let's Get Started</h2>
        <p className="text-neutral-600 text-lg">Tell us about your HVAC project so we can provide accurate load calculations</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-8">
        <FormField label="Project Name" required>
          <Input
            type="text"
            required
            value={formData.projectName}
            onChange={(e) => setFormData({ ...formData, projectName: e.target.value })}
            placeholder="e.g., Smith Residence HVAC Design"
            leftIcon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            }
          />
        </FormField>

        <FormField 
          label="ZIP Code" 
          required
          helperText="We'll automatically determine your climate zone and local building requirements"
        >
          <Input
            type="text"
            required
            pattern="[0-9]{5}"
            value={formData.zipCode}
            onChange={(e) => setFormData({ ...formData, zipCode: e.target.value })}
            placeholder="Enter 5-digit ZIP code"
            leftIcon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            }
          />
        </FormField>

        <FormField label="Project Type">
          <SelectionGrid
            options={[
              {
                value: 'residential',
                title: 'Residential',
                description: 'Homes, condos, apartments',
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                )
              },
              {
                value: 'commercial',
                title: 'Commercial',
                description: 'Offices, retail, warehouses',
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                )
              }
            ]}
            selectedValue={formData.projectType}
            onSelect={(value) => setFormData({ ...formData, projectType: value as 'residential' | 'commercial' })}
          />
        </FormField>

        <FormField label="Construction Type">
          <SelectionGrid
            options={[
              {
                value: 'new',
                title: 'New Construction',
                description: 'Fresh build, modern codes',
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                  </svg>
                )
              },
              {
                value: 'retrofit',
                title: 'Retrofit/Replacement',
                description: 'Upgrading existing system',
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                )
              }
            ]}
            selectedValue={formData.constructionType}
            onSelect={(value) => setFormData({ ...formData, constructionType: value as 'new' | 'retrofit' })}
          />
        </FormField>

        <FormField label="How would you like to input project details?">
          <SelectionGrid
            options={[
              {
                value: 'blueprint',
                title: 'Upload Blueprint',
                description: 'AI analyzes your plans automatically',
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                )
              },
              {
                value: 'manual',
                title: 'Manual Entry',
                description: 'Enter room details step-by-step',
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                )
              }
            ]}
            selectedValue={inputMethod}
            onSelect={(value) => setInputMethod(value as 'manual' | 'blueprint')}
          />
        </FormField>

        <div className="flex justify-center pt-6">
          <Button 
            type="submit" 
            size="lg" 
            fullWidth={true}
            rightIcon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            }
          >
            {inputMethod === 'blueprint' ? 'Continue to Blueprint Upload' : 'Continue to Building Details'}
          </Button>
        </div>
      </form>
    </Card>
  );
}