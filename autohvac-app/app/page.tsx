'use client';

import ProjectSetup from './components/ProjectSetup';
import BuildingInput from './components/BuildingInput';
import RoomInput from './components/RoomInput';
import Results from './components/Results';
import BlueprintUpload from './components/BlueprintUpload';
import ProfessionalResults from './components/ProfessionalResults';
import { ProgressIndicator, ErrorState, Header } from './components/ui';
import ErrorBoundary from './components/ErrorBoundary';
import { useAppStore } from './store/useAppStore';

export default function Home() {
  const {
    // State
    currentStep,
    projectInfo,
    buildingInfo,
    rooms,
    inputMethod,
    loadCalculation,
    recommendations,
    isCalculating,
    calculationError,
    blueprintJobId,
    professionalAnalysis,
    isProcessing,
    processingError,
    
    // Actions
    setProjectInfo,
    setBuildingInfo,
    setRooms,
    navigateToStep,
    navigateBack,
    startOver,
    performCalculations,
    clearCalculations,
    handleBlueprintUpload,
    handleBlueprintError,
    clearBlueprintData,
    
    // Computed
    canNavigateBack,
    isComplete,
    hasCalculationResults,
    hasBlueprintAnalysis,
  } = useAppStore();

  const handleProjectSubmit = (data: any) => {
    setProjectInfo(data);
  };

  const handleBuildingSubmit = (data: any) => {
    setBuildingInfo(data);
  };

  const handleRoomsSubmit = async (roomData: any) => {
    setRooms(roomData);
    
    if (projectInfo && buildingInfo) {
      await performCalculations(roomData, buildingInfo, projectInfo);
    }
  };

  const handleBlueprintUploadWrapper = async (jobId: string, fileNames: string[]) => {
    await handleBlueprintUpload(jobId, fileNames);
  };

  const handleStartOver = () => {
    startOver();
  };

  const progressSteps = inputMethod === 'manual' 
    ? [
        { id: 'project', label: 'Project' },
        { id: 'building', label: 'Building' },
        { id: 'rooms', label: 'Rooms' },
        { id: 'results', label: 'Results' }
      ]
    : [
        { id: 'project', label: 'Project' },
        { id: 'blueprint', label: 'Blueprint' },
        { id: 'results', label: 'Results' }
      ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-25 via-white to-primary-25/30">
      <Header />
      
      <main className="max-w-6xl mx-auto px-4 py-8 lg:py-12">
        <ProgressIndicator 
          steps={progressSteps}
          currentStep={currentStep}
        />

      {/* Main Content */}
      <ErrorBoundary onError={(error, errorInfo) => {
        // Log error to monitoring service in production
        console.error('Application error:', error, errorInfo);
      }}>
        <div className="min-h-[600px]">
          {currentStep === 'project' && (
            <ProjectSetup onSubmit={handleProjectSubmit} />
          )}
          {currentStep === 'building' && (
            <BuildingInput 
              onSubmit={handleBuildingSubmit} 
              onBack={navigateBack}
              projectInfo={projectInfo!}
            />
          )}
          {currentStep === 'rooms' && (
            <RoomInput 
              onSubmit={handleRoomsSubmit} 
              onBack={navigateBack}
              buildingInfo={buildingInfo!}
            />
          )}
          {currentStep === 'blueprint' && (
            <div className="card max-w-3xl mx-auto">
              <h2 className="text-2xl font-bold mb-6 text-hvac-navy">Upload Your Blueprint</h2>
              <BlueprintUpload 
                onUploadComplete={handleBlueprintUploadWrapper}
                onError={handleBlueprintError}
                projectInfo={projectInfo}
              />
              <div className="mt-6 flex justify-between">
                <button
                  onClick={navigateBack}
                  className="btn-secondary"
                >
                  Back
                </button>
              </div>
            </div>
          )}
          {currentStep === 'results' && (
            hasBlueprintAnalysis() ? (
              <ProfessionalResults 
                analysisData={professionalAnalysis}
                onStartOver={handleStartOver}
              />
            ) : hasCalculationResults() ? (
              <Results 
                projectInfo={projectInfo!}
                buildingInfo={buildingInfo!}
                rooms={rooms}
                loadCalculation={loadCalculation!}
                recommendations={recommendations}
                onStartOver={handleStartOver}
              />
            ) : isCalculating ? (
              <ErrorState
                title="Calculating..."
                message="Please wait while we process your HVAC load calculations."
                icon="network"
                showRetry={false}
              />
            ) : calculationError ? (
              <ErrorState
                title="Calculation Error"
                message={calculationError}
                onRetry={() => {
                  if (projectInfo && buildingInfo) {
                    performCalculations(rooms, buildingInfo, projectInfo);
                  }
                }}
                onReset={handleStartOver}
                showReset={true}
              />
            ) : processingError ? (
              <ErrorState
                title="Blueprint Processing Error"
                message={processingError}
                onRetry={() => {
                  clearBlueprintData();
                  navigateToStep('blueprint');
                }}
                onReset={handleStartOver}
                showReset={true}
              />
            ) : (
              <ErrorState
                title="No Results Available"
                message="We couldn't generate results for your project. Please try again or start over."
                onReset={handleStartOver}
                showRetry={false}
                showReset={true}
              />
            )
          )}
        </div>
      </ErrorBoundary>
      </main>
      
      {/* Footer */}
      <footer className="border-t border-neutral-200 bg-white/80 backdrop-blur-sm mt-20">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between text-sm text-neutral-600">
            <div className="flex items-center space-x-2 mb-4 sm:mb-0">
              <div className="w-6 h-6 bg-gradient-to-br from-primary-600 to-primary-700 rounded flex items-center justify-center">
                <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <span className="font-medium">© 2024 AutoHVAC Pro. Professional-grade HVAC solutions.</span>
            </div>
            <div className="flex items-center space-x-4 text-xs">
              <span className="badge">ACCA Compliant</span>
              <span className="badge-success">Manual J Certified</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}