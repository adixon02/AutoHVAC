'use client';

import { useState } from 'react';
import ProjectSetup from './components/ProjectSetup';
import BuildingInput from './components/BuildingInput';
import RoomInput from './components/RoomInput';
import Results from './components/Results';
import BlueprintUpload from './components/BlueprintUpload';
import { ProjectInfo, BuildingInfo, Room, LoadCalculation, SystemRecommendation } from './lib/types';
import { getClimateZone, defaultClimateZone } from './lib/climateData';
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

  const handleRoomsSubmit = (roomData: Room[]) => {
    setRooms(roomData);
    
    // Perform calculations
    if (projectInfo && buildingInfo) {
      const climate = getClimateZone(projectInfo.zipCode) || defaultClimateZone;
      const loadCalc = calculateTotalLoad(roomData, buildingInfo, climate);
      setLoadCalculation(loadCalc);
      
      const recs = generateSystemRecommendations(loadCalc, buildingInfo);
      setRecommendations(recs);
      
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
        if (inputMethod === 'manual') {
          setCurrentStep('rooms');
        } else {
          setCurrentStep('blueprint');
        }
        break;
      case 'blueprint':
        setCurrentStep('project');
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
  };

  const handleBlueprintUpload = async (file: File) => {
    try {
      // Simulate blueprint processing
      console.log('Processing blueprint:', file.name);
      
      // Mock processing delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Mock successful processing
      const mockJobId = 'job_' + Math.random().toString(36).substr(2, 9);
      setBlueprintJobId(mockJobId);
      
      // Mock results - in real app this would come from backend
      const mockBuildingInfo: BuildingInfo = {
        squareFootage: 2400,
        ceilingHeight: 9,
        insulationQuality: 'good' as const,
        windowType: 'double' as const,
        yearBuilt: 2020,
        stories: 2
      };
      
      const mockRooms: Room[] = [
        {
          id: '1',
          name: 'Living Room',
          area: 320,
          ceilingHeight: 9,
          windowArea: 48,
          exteriorWalls: 2,
          occupancy: 4,
          roomType: 'living'
        },
        {
          id: '2', 
          name: 'Master Bedroom',
          area: 200,
          ceilingHeight: 9,
          windowArea: 24,
          exteriorWalls: 2,
          occupancy: 2,
          roomType: 'bedroom'
        }
      ];
      
      setBuildingInfo(mockBuildingInfo);
      setRooms(mockRooms);
      
      if (projectInfo) {
        const climate = getClimateZone(projectInfo.zipCode) || defaultClimateZone;
        const loadCalc = calculateTotalLoad(mockRooms, mockBuildingInfo, climate);
        setLoadCalculation(loadCalc);
        
        const recs = generateSystemRecommendations(loadCalc, mockBuildingInfo);
        setRecommendations(recs);
        
        setCurrentStep('results');
      }
    } catch (error) {
      console.error('Blueprint processing failed:', error);
      handleBlueprintError(error as string);
    }
  };

  const handleBlueprintError = (error: string) => {
    console.error('Blueprint upload error:', error);
    alert(`Blueprint processing failed: ${error}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 lg:px-8">
      {/* Hero Section */}
      <div className="text-center mb-16 animate-fade-in-up">
        <h1 className="page-header">
          AI-Powered HVAC Design
        </h1>
        <p className="page-subtitle mx-auto">
          Professional Manual J calculations and system recommendations in minutes, not hours. 
          Built for contractors, engineers, and HVAC professionals.
        </p>
      </div>

      {/* Premium Progress Indicator */}
      <div className="mb-16">
        <div className="flex items-center justify-center max-w-4xl mx-auto">
          {inputMethod === 'manual' 
            ? ['project', 'building', 'rooms', 'results'].map((step, index) => {
              const stepNames = ['Project Setup', 'Building Details', 'Room Analysis', 'AI Results'];
              const stepIndex = ['project', 'building', 'rooms', 'results'].indexOf(currentStep);
              const isActive = currentStep === step;
              const isCompleted = stepIndex > index;
              
              return (
                <div key={step} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={`progress-step ${
                        isActive ? 'progress-step-active' : 
                        isCompleted ? 'progress-step-completed' : 'progress-step-pending'
                      }`}
                    >
                      {isCompleted ? (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>
                    <span className={`text-sm font-medium mt-3 ${
                      isActive ? 'text-primary-700' : 
                      isCompleted ? 'text-accent-emerald' : 'text-industrial-500'
                    }`}>
                      {stepNames[index]}
                    </span>
                  </div>
                  {index < 3 && (
                    <div className={`progress-connector w-24 mx-6 ${
                      stepIndex > index ? 'progress-connector-active' : 'progress-connector-pending'
                    }`} />
                  )}
                </div>
              );
            })
            : ['project', 'blueprint', 'results'].map((step, index) => {
              const stepNames = ['Project Setup', 'Blueprint AI', 'AI Results'];
              const stepIndex = ['project', 'blueprint', 'results'].indexOf(currentStep);
              const isActive = currentStep === step;
              const isCompleted = stepIndex > index;
              
              return (
                <div key={step} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={`progress-step ${
                        isActive ? 'progress-step-active' : 
                        isCompleted ? 'progress-step-completed' : 'progress-step-pending'
                      }`}
                    >
                      {isCompleted ? (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>
                    <span className={`text-sm font-medium mt-3 ${
                      isActive ? 'text-primary-700' : 
                      isCompleted ? 'text-accent-emerald' : 'text-industrial-500'
                    }`}>
                      {stepNames[index]}
                    </span>
                  </div>
                  {index < 2 && (
                    <div className={`progress-connector w-24 mx-6 ${
                      stepIndex > index ? 'progress-connector-active' : 'progress-connector-pending'
                    }`} />
                  )}
                </div>
              );
            })
          }
        </div>
      </div>

      {/* Main Content */}
      <div className="min-h-[600px] animate-fade-in-up" style={{animationDelay: '0.2s'}}>
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
          <div className="card-premium max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-primary rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-glow">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-industrial-900 mb-4">
                AI Blueprint Analysis
              </h2>
              <p className="text-lg text-industrial-600 max-w-2xl mx-auto">
                Upload your architectural drawings and our AI will automatically detect rooms, 
                calculate dimensions, and generate Manual J calculations.
              </p>
            </div>
            
            <BlueprintUpload 
              onUploadComplete={handleBlueprintUpload}
              onError={handleBlueprintError}
            />
            
            <div className="flex justify-between items-center mt-8 pt-6 border-t border-industrial-200/50">
              <button
                onClick={handleBack}
                className="btn-secondary"
              >
                <span className="btn-text">← Back to Project</span>
              </button>
              
              <div className="flex items-center text-sm text-industrial-600">
                <svg className="w-4 h-4 mr-2 text-accent-emerald" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                Your files are encrypted and secure
              </div>
            </div>
          </div>
        )}
        {currentStep === 'results' && loadCalculation && recommendations.length > 0 && (
          <Results
            projectInfo={projectInfo!}
            buildingInfo={buildingInfo!}
            rooms={rooms}
            loadCalculation={loadCalculation}
            recommendations={recommendations}
            onStartOver={handleStartOver}
          />
        )}
      </div>
    </div>
  );
}