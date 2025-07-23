'use client';

import { useState } from 'react';
import ProjectSetup from './components/ProjectSetup';
import BuildingInput from './components/BuildingInput';
import RoomInput from './components/RoomInput';
import Results from './components/Results';
import BlueprintUpload from './components/BlueprintUpload';
import ProfessionalResults from './components/ProfessionalResults';
import { ProjectInfo, BuildingInfo, Room, LoadCalculation, SystemRecommendation } from './lib/types';
import { getClimateZone, getClimateZoneSync, defaultClimateZone } from './lib/climateData';
import { calculateTotalLoad } from './lib/manualJ';
import { generateSystemRecommendations } from './lib/systemRecommendations';

type Step = 'project' | 'building' | 'rooms' | 'results' | 'blueprint';

export default function Home() {
  const [currentStep, setCurrentStep] = useState<Step>('project');
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [buildingInfo, setBuildingInfo] = useState<BuildingInfo | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loadCalculation, setLoadCalculation] = useState<LoadCalculation | null>(null);
  const [recommendations, setRecommendations] = useState<SystemRecommendation[]>([]);
  const [blueprintJobId, setBlueprintJobId] = useState<string | null>(null);
  const [inputMethod, setInputMethod] = useState<'manual' | 'blueprint'>('manual');
  const [professionalAnalysis, setProfessionalAnalysis] = useState<any>(null);

  const handleProjectSubmit = (data: ProjectInfo) => {
    setProjectInfo(data);
    setInputMethod(data.inputMethod || 'manual');
    
    if (data.inputMethod === 'blueprint') {
      setCurrentStep('blueprint');
    } else {
      setCurrentStep('building');
    }
  };

  const handleBuildingSubmit = (data: BuildingInfo) => {
    setBuildingInfo(data);
    setCurrentStep('rooms');
  };

  const handleRoomsSubmit = async (roomData: Room[]) => {
    setRooms(roomData);
    
    // Perform calculations
    if (projectInfo && buildingInfo) {
      // Try to get climate data from API, fallback to sync version
      let climate = await getClimateZone(projectInfo.zipCode);
      if (!climate) {
        climate = getClimateZoneSync(projectInfo.zipCode) || defaultClimateZone;
      }
      
      const loadCalc = calculateTotalLoad(roomData, buildingInfo, climate);
      setLoadCalculation(loadCalc);
      
      const systemRecs = generateSystemRecommendations(loadCalc, buildingInfo);
      setRecommendations(systemRecs);
      
      setCurrentStep('results');
    }
  };

  const handleBack = () => {
    switch (currentStep) {
      case 'building':
        setCurrentStep('project');
        break;
      case 'rooms':
        setCurrentStep('building');
        break;
      case 'results':
        setCurrentStep('rooms');
        break;
    }
  };

  const handleStartOver = () => {
    setCurrentStep('project');
    setProjectInfo(null);
    setBuildingInfo(null);
    setRooms([]);
    setLoadCalculation(null);
    setRecommendations([]);
    setBlueprintJobId(null);
    setInputMethod('manual');
    setProfessionalAnalysis(null);
  };

  const handleBlueprintUpload = async (jobId: string, fileNames: string[]) => {
    console.log('🎯 handleBlueprintUpload called with jobId:', jobId, 'files:', fileNames);
    setBlueprintJobId(jobId);
    
    // This function is called when processing is COMPLETE
    // So we can immediately get the results
    try {
      console.log('📡 Fetching results from:', `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/results/${jobId}`);
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/results/${jobId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('📊 Professional analysis data received:', data);
      
      if (data.status === 'completed') {
        console.log('✅ Analysis completed successfully! Moving to results...');
        // Move to results step and show professional analysis
        setCurrentStep('results');
        setProfessionalAnalysis(data);
      } else {
        // If somehow not complete, show an error
        console.log('❌ Unexpected status:', data.status, data);
        handleBlueprintError(`Analysis status: ${data.status}. Expected 'completed'.`);
      }
    } catch (error) {
      console.error('❌ Failed to get analysis results:', error);
      handleBlueprintError(`API Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleBlueprintError = (error: string) => {
    console.error('Blueprint upload error:', error);
    alert(`Blueprint processing failed: ${error}`);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Progress Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-center">
          {inputMethod === 'manual' 
            ? ['project', 'building', 'rooms', 'results'].map((step, index) => (
            <div key={step} className="flex items-center">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center font-semibold
                  ${currentStep === step ? 'bg-hvac-blue text-white' : 
                    ['project', 'building', 'rooms', 'results'].indexOf(currentStep) > index ? 
                    'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'}
                `}
              >
                {index + 1}
              </div>
              {index < 3 && (
                <div className={`w-24 h-1 mx-2 ${
                  ['project', 'building', 'rooms', 'results'].indexOf(currentStep) > index ? 
                  'bg-green-500' : 'bg-gray-300'
                }`} />
              )}
            </div>
          ))
            : ['project', 'blueprint', 'results'].map((step, index) => (
            <div key={step} className="flex items-center">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center font-semibold
                  ${currentStep === step ? 'bg-hvac-blue text-white' : 
                    ['project', 'blueprint', 'results'].indexOf(currentStep) > index ? 
                    'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'}
                `}
              >
                {index + 1}
              </div>
              {index < 2 && (
                <div className={`w-24 h-1 mx-2 ${
                  ['project', 'blueprint', 'results'].indexOf(currentStep) > index ? 
                  'bg-green-500' : 'bg-gray-300'
                }`} />
              )}
            </div>
          ))
          }
        </div>
        <div className="flex justify-around mt-2 text-sm">
          {inputMethod === 'manual' ? (
            <>
              <span className={currentStep === 'project' ? 'font-semibold' : ''}>Project</span>
              <span className={currentStep === 'building' ? 'font-semibold' : ''}>Building</span>
              <span className={currentStep === 'rooms' ? 'font-semibold' : ''}>Rooms</span>
              <span className={currentStep === 'results' ? 'font-semibold' : ''}>Results</span>
            </>
          ) : (
            <>
              <span className={currentStep === 'project' ? 'font-semibold' : ''}>Project</span>
              <span className={currentStep === 'blueprint' ? 'font-semibold' : ''}>Blueprint</span>
              <span className={currentStep === 'results' ? 'font-semibold' : ''}>Results</span>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="min-h-[600px]">
        {currentStep === 'project' && (
          <ProjectSetup onSubmit={handleProjectSubmit} />
        )}
        {currentStep === 'building' && (
          <BuildingInput 
            onSubmit={handleBuildingSubmit} 
            onBack={handleBack}
            projectInfo={projectInfo!}
          />
        )}
        {currentStep === 'rooms' && (
          <RoomInput 
            onSubmit={handleRoomsSubmit} 
            onBack={handleBack}
            buildingInfo={buildingInfo!}
          />
        )}
        {currentStep === 'blueprint' && (
          <div className="card max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold mb-6 text-hvac-navy">Upload Your Blueprint</h2>
            <BlueprintUpload 
              onUploadComplete={handleBlueprintUpload}
              onError={handleBlueprintError}
              projectInfo={projectInfo}
            />
            <div className="mt-6 flex justify-between">
              <button
                onClick={handleBack}
                className="btn-secondary"
              >
                Back
              </button>
            </div>
          </div>
        )}
        {currentStep === 'results' && (
          professionalAnalysis ? (
            <ProfessionalResults 
              analysisData={professionalAnalysis}
              onStartOver={handleStartOver}
            />
          ) : loadCalculation ? (
            <Results 
              projectInfo={projectInfo!}
              buildingInfo={buildingInfo!}
              rooms={rooms}
              loadCalculation={loadCalculation}
              recommendations={recommendations}
              onStartOver={handleStartOver}
            />
          ) : null
        )}
      </div>
    </div>
  );
}