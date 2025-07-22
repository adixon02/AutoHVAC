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
  };

  const handleBlueprintUpload = async (jobId: string, fileName: string) => {
    setBlueprintJobId(jobId);
    // Process blueprint analysis
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/blueprint/analyze/${jobId}`);
      const data = await response.json();
      
      // Convert blueprint data to rooms
      if (data.data && data.data.rooms) {
        const processedRooms: Room[] = data.data.rooms.map((room: any, index: number) => ({
          id: `room-${index}`,
          name: room.name,
          area: room.area,
          ceilingHeight: 9, // Default, could be extracted from blueprint
          windowArea: room.features?.windows ? room.features.windows * 15 : 20,
          exteriorWalls: room.features?.exterior_walls || 0,
          occupancy: room.type === 'bedroom' ? 2 : 4
        }));
        
        setRooms(processedRooms);
        
        // Set building info from blueprint
        setBuildingInfo({
          squareFootage: data.data.total_area,
          stories: 1, // Would need to be extracted
          ceilingHeight: 9,
          foundationType: 'slab',
          insulationQuality: 'average',
          windowType: 'double',
          windowArea: processedRooms.reduce((sum, room) => sum + room.windowArea, 0),
          orientation: 'north'
        });
        
        // Calculate loads
        const climate = getClimateZone(projectInfo!.zipCode) || defaultClimateZone;
        const loadCalc = calculateTotalLoad(processedRooms, {
          squareFootage: data.data.total_area,
          stories: 1,
          ceilingHeight: 9,
          foundationType: 'slab',
          insulationQuality: 'average',
          windowType: 'double',
          windowArea: processedRooms.reduce((sum, room) => sum + room.windowArea, 0),
          orientation: 'north'
        }, climate);
        setLoadCalculation(loadCalc);
        
        const systemRecs = generateSystemRecommendations(loadCalc, {
          squareFootage: data.data.total_area,
          stories: 1,
          ceilingHeight: 9,
          foundationType: 'slab',
          insulationQuality: 'average',
          windowType: 'double',
          windowArea: processedRooms.reduce((sum, room) => sum + room.windowArea, 0),
          orientation: 'north'
        });
        setRecommendations(systemRecs);
        
        setCurrentStep('results');
      }
    } catch (error) {
      console.error('Failed to analyze blueprint:', error);
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
        {currentStep === 'results' && loadCalculation && (
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