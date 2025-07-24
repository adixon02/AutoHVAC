'use client';

import { useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { ProgressIndicator } from '@/components/layout/ProgressIndicator';
import { ProjectForm } from '@/components/forms/ProjectForm';
import { BlueprintUpload } from '@/components/forms/BlueprintUpload';
import { Alert, Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { useAppStore } from '@/store/useAppStore';
import type { ProjectData } from '@/components/forms/ProjectForm';

export default function App() {
  const {
    // State
    currentStep,
    project,
    building,
    rooms,
    climate,
    loadCalculation,
    recommendations,
    processing,
    errors,
    blueprintJobId,
    
    // Actions
    setCurrentStep,
    navigateBack,
    startOver,
    setProject,
    handleBlueprintUpload,
    performCalculations,
    clearAllErrors,
    canNavigateBack,
    isReadyForCalculations,
    hasResults,
  } = useAppStore();

  // Clear errors when step changes
  useEffect(() => {
    clearAllErrors();
  }, [currentStep, clearAllErrors]);

  // Define progress steps
  const getProgressSteps = () => {
    const baseSteps = [
      {
        id: 'project',
        name: 'Project',
        status: currentStep === 'project' ? 'current' as const : 
               ['input', 'results'].includes(currentStep) ? 'complete' as const : 'upcoming' as const
      },
      {
        id: 'input',
        name: project?.inputMethod === 'blueprint' ? 'Blueprint' : 'Building Details',
        status: currentStep === 'input' ? 'current' as const :
               currentStep === 'results' ? 'complete' as const : 'upcoming' as const
      },
      {
        id: 'results',
        name: 'Results',
        status: currentStep === 'results' ? 'current' as const : 'upcoming' as const
      }
    ];
    
    return baseSteps;
  };

  // Handle project form submission
  const handleProjectSubmit = (data: ProjectData) => {
    const projectInfo = {
      id: `project-${Date.now()}`,
      projectName: data.projectName,
      zipCode: data.zipCode,
      buildingType: data.buildingType,
      constructionType: data.constructionType,
      inputMethod: data.inputMethod,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    setProject(projectInfo);
    setCurrentStep('input');
  };

  // Handle blueprint upload completion
  const handleBlueprintComplete = (jobId: string, fileNames: string[]) => {
    handleBlueprintUpload(jobId, fileNames);
  };

  // Handle blueprint upload error
  const handleBlueprintError = (errorMessage: string) => {
    console.error('Blueprint upload error:', errorMessage);
  };

  // Handle switching to manual input
  const handleSwitchToManual = () => {
    if (project) {
      const updatedProject = { ...project, inputMethod: 'manual' as const };
      setProject(updatedProject);
      alert('Manual input forms would be implemented here in V1 completion!');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50/30 to-white">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Progress Indicator */}
        <ProgressIndicator steps={getProgressSteps()} />
        
        {/* Global Errors */}
        {Object.entries(errors).map(([key, message]) => (
          <div key={key} className="mb-6">
            <Alert variant="error" title="Error">
              {message}
            </Alert>
          </div>
        ))}
        
        {/* Processing Status */}
        {processing.status !== 'idle' && (
          <div className="mb-6">
            <Alert 
              variant={processing.status === 'error' ? 'error' : 
                     processing.status === 'completed' ? 'success' : 'info'}
              title={processing.status === 'processing' ? 'Processing...' : 
                     processing.status === 'completed' ? 'Complete!' : 
                     processing.status === 'error' ? 'Error' : 'Status'}
            >
              {processing.message}
              {processing.status === 'processing' && processing.progress > 0 && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${processing.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </Alert>
          </div>
        )}
        
        {/* Step Content */}
        {currentStep === 'project' && (
          <ProjectForm
            initialData={project ? {
              projectName: project.projectName,
              zipCode: project.zipCode,
              buildingType: project.buildingType,
              constructionType: project.constructionType,
              inputMethod: project.inputMethod,
            } : undefined}
            onSubmit={handleProjectSubmit}
            onBack={canNavigateBack() ? navigateBack : undefined}
            loading={processing.status === 'processing'}
          />
        )}
        
        {currentStep === 'input' && project && (
          <>
            {project.inputMethod === 'blueprint' ? (
              <BlueprintUpload
                projectData={{
                  projectName: project.projectName,
                  zipCode: project.zipCode,
                  buildingType: project.buildingType,
                  constructionType: project.constructionType,
                  inputMethod: project.inputMethod,
                }}
                onUploadComplete={handleBlueprintComplete}
                onError={handleBlueprintError}
                onBack={navigateBack}
                onSwitchToManual={handleSwitchToManual}
              />
            ) : (
              <Card className="w-full max-w-2xl mx-auto">
                <CardHeader>
                  <CardTitle>Manual Entry</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">
                      Manual Building Entry Forms
                    </h3>
                    <p className="text-gray-600 mb-6">
                      Building details and room entry forms would be implemented here for V1 completion.
                      This would include the BuildingForm and RoomForm components.
                    </p>
                    <div className="space-x-4">
                      <Button variant="outline" onClick={navigateBack}>
                        Back to Project
                      </Button>
                      <Button onClick={() => alert('Manual forms coming in V1 completion!')}>
                        Continue with Manual Entry
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
        
        {currentStep === 'results' && (
          <Card className="w-full max-w-4xl mx-auto">
            <CardHeader>
              <CardTitle>HVAC Load Calculation Results</CardTitle>
            </CardHeader>
            <CardContent>
              {hasResults() && loadCalculation && recommendations ? (
                <div className="space-y-8">
                  {/* Load Summary */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-blue-50 p-6 rounded-lg">
                      <h3 className="text-lg font-semibold text-blue-900 mb-2">Cooling Load</h3>
                      <p className="text-3xl font-bold text-blue-700">
                        {loadCalculation.coolingTons} tons
                      </p>
                      <p className="text-sm text-blue-600">
                        {loadCalculation.totalCoolingLoad.toLocaleString()} BTU/hr
                      </p>
                    </div>
                    <div className="bg-red-50 p-6 rounded-lg">
                      <h3 className="text-lg font-semibold text-red-900 mb-2">Heating Load</h3>
                      <p className="text-3xl font-bold text-red-700">
                        {loadCalculation.heatingTons} tons
                      </p>
                      <p className="text-sm text-red-600">
                        {loadCalculation.totalHeatingLoad.toLocaleString()} BTU/hr
                      </p>
                    </div>
                  </div>
                  
                  {/* Project Info */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-gray-900 mb-2">Project Details</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Project:</span>
                        <p className="font-medium">{project?.projectName}</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Location:</span>
                        <p className="font-medium">{project?.zipCode} ({climate?.zone})</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Building:</span>
                        <p className="font-medium">{building?.totalSquareFootage} sq ft</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Rooms:</span>
                        <p className="font-medium">{rooms.length} rooms</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* System Recommendations */}
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-4">
                      Equipment Recommendations
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {recommendations.map((rec) => (
                        <div key={rec.tier} className="border rounded-lg p-6">
                          <div className="text-center mb-4">
                            <h4 className="text-lg font-semibold capitalize mb-2">
                              {rec.tier} Tier
                            </h4>
                          </div>
                          <div className="space-y-4">
                            <div>
                              <h5 className="font-medium text-gray-900">Cooling System</h5>
                              <p className="text-sm text-gray-600">
                                {rec.coolingSystem.brand} {rec.coolingSystem.type}
                              </p>
                              <p className="text-sm">
                                {rec.coolingSystem.size} tons, {rec.coolingSystem.seer} SEER
                              </p>
                              <p className="text-sm font-medium text-green-600">
                                ${rec.coolingSystem.estimatedCost.toLocaleString()}
                              </p>
                            </div>
                            <div>
                              <h5 className="font-medium text-gray-900">Heating System</h5>
                              <p className="text-sm text-gray-600">
                                {rec.heatingSystem.brand} {rec.heatingSystem.type}
                              </p>
                              <p className="text-sm">
                                {rec.heatingSystem.size.toLocaleString()} BTU/hr, 
                                {Math.round(rec.heatingSystem.efficiency * 100)}% efficiency
                              </p>
                              {rec.heatingSystem.estimatedCost > 0 && (
                                <p className="text-sm font-medium text-green-600">
                                  ${rec.heatingSystem.estimatedCost.toLocaleString()}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex justify-between pt-6">
                    <Button variant="outline" onClick={navigateBack}>
                      Back
                    </Button>
                    <div className="space-x-4">
                      <Button variant="outline" onClick={startOver}>
                        New Project
                      </Button>
                      <Button onClick={() => alert('PDF report generation coming soon!')}>
                        Download Report
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">No calculation results available.</p>
                  <Button onClick={navigateBack}>Go Back</Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}