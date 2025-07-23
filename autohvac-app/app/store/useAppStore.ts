'use client';

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { ProjectInfo, BuildingInfo, Room, LoadCalculation, SystemRecommendation } from '../lib/types';
import { getClimateZone, getClimateZoneSync, defaultClimateZone } from '../lib/climateData';
import { calculateTotalLoad } from '../lib/manualJ';
import { generateSystemRecommendations } from '../lib/systemRecommendations';

type Step = 'project' | 'building' | 'rooms' | 'results' | 'blueprint';

interface AppState {
  // Project State
  currentStep: Step;
  projectInfo: ProjectInfo | null;
  buildingInfo: BuildingInfo | null;
  rooms: Room[];
  inputMethod: 'manual' | 'blueprint';
  
  // Calculations State
  loadCalculation: LoadCalculation | null;
  recommendations: SystemRecommendation[];
  isCalculating: boolean;
  calculationError: string | null;
  
  // Blueprint State
  blueprintJobId: string | null;
  professionalAnalysis: any | null;
  isProcessing: boolean;
  processingError: string | null;
}

interface AppActions {
  // Project Actions
  setProjectInfo: (data: ProjectInfo) => void;
  setBuildingInfo: (data: BuildingInfo) => void;
  setRooms: (data: Room[]) => void;
  navigateToStep: (step: Step) => void;
  navigateBack: () => void;
  startOver: () => void;
  
  // Calculation Actions
  performCalculations: (rooms: Room[], buildingInfo: BuildingInfo, projectInfo: ProjectInfo) => Promise<void>;
  clearCalculations: () => void;
  
  // Blueprint Actions
  handleBlueprintUpload: (jobId: string, fileNames: string[]) => Promise<void>;
  handleBlueprintError: (error: string) => void;
  clearBlueprintData: () => void;
  
  // Computed getters
  canNavigateBack: () => boolean;
  isComplete: () => boolean;
  hasCalculationResults: () => boolean;
  hasBlueprintAnalysis: () => boolean;
}

type AppStore = AppState & AppActions;

const initialState: AppState = {
  // Project State
  currentStep: 'project',
  projectInfo: null,
  buildingInfo: null,
  rooms: [],
  inputMethod: 'manual',
  
  // Calculations State
  loadCalculation: null,
  recommendations: [],
  isCalculating: false,
  calculationError: null,
  
  // Blueprint State
  blueprintJobId: null,
  professionalAnalysis: null,
  isProcessing: false,
  processingError: null,
};

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        // Project Actions
        setProjectInfo: (data: ProjectInfo) => {
          set((state) => ({
            projectInfo: data,
            inputMethod: data.inputMethod || 'manual',
            currentStep: data.inputMethod === 'blueprint' ? 'blueprint' : 'building'
          }), false, 'setProjectInfo');
        },
        
        setBuildingInfo: (data: BuildingInfo) => {
          set({ buildingInfo: data, currentStep: 'rooms' }, false, 'setBuildingInfo');
        },
        
        setRooms: (data: Room[]) => {
          set({ rooms: data, currentStep: 'results' }, false, 'setRooms');
        },
        
        navigateToStep: (step: Step) => {
          set({ currentStep: step }, false, 'navigateToStep');
        },
        
        navigateBack: () => {
          const { currentStep, inputMethod } = get();
          let newStep: Step = 'project';
          
          switch (currentStep) {
            case 'building':
              newStep = 'project';
              break;
            case 'rooms':
              newStep = 'building';
              break;
            case 'results':
              newStep = inputMethod === 'blueprint' ? 'blueprint' : 'rooms';
              break;
            case 'blueprint':
              newStep = 'project';
              break;
          }
          
          set({ currentStep: newStep }, false, 'navigateBack');
        },
        
        startOver: () => {
          set({ ...initialState }, false, 'startOver');
        },
        
        // Calculation Actions
        performCalculations: async (rooms: Room[], buildingInfo: BuildingInfo, projectInfo: ProjectInfo) => {
          if (!rooms.length || !buildingInfo || !projectInfo) {
            set({ calculationError: 'Missing required data for calculations' }, false, 'performCalculations:error');
            return;
          }

          set({ isCalculating: true, calculationError: null }, false, 'performCalculations:start');

          try {
            // Try to get climate data from API, fallback to sync version
            let climate = await getClimateZone(projectInfo.zipCode);
            if (!climate) {
              climate = getClimateZoneSync(projectInfo.zipCode) || defaultClimateZone;
            }
            
            // Perform load calculations
            const loadCalc = calculateTotalLoad(rooms, buildingInfo, climate);
            
            // Generate system recommendations
            const systemRecs = generateSystemRecommendations(loadCalc, buildingInfo);
            
            set({ 
              loadCalculation: loadCalc,
              recommendations: systemRecs,
              isCalculating: false
            }, false, 'performCalculations:success');
            
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Calculation failed';
            set({ 
              calculationError: errorMessage,
              isCalculating: false 
            }, false, 'performCalculations:error');
            console.error('Calculation error:', error);
          }
        },
        
        clearCalculations: () => {
          set({
            loadCalculation: null,
            recommendations: [],
            calculationError: null,
            isCalculating: false
          }, false, 'clearCalculations');
        },
        
        // Blueprint Actions
        handleBlueprintUpload: async (jobId: string, fileNames: string[]) => {
          console.log('🎯 handleBlueprintUpload called with jobId:', jobId, 'files:', fileNames);
          
          set({ 
            blueprintJobId: jobId,
            isProcessing: true,
            processingError: null 
          }, false, 'handleBlueprintUpload:start');
          
          try {
            console.log('📡 Fetching results from:', `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/results/${jobId}`);
            
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/blueprint/results/${jobId}`);
            
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 Professional analysis data received:', data);
            
            if (data.status === 'completed') {
              console.log('✅ Analysis completed successfully!');
              set({ 
                professionalAnalysis: data,
                isProcessing: false,
                currentStep: 'results'
              }, false, 'handleBlueprintUpload:success');
            } else {
              throw new Error(`Analysis status: ${data.status}. Expected 'completed'.`);
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            console.error('❌ Failed to get analysis results:', error);
            set({ 
              processingError: `API Error: ${errorMessage}`,
              isProcessing: false 
            }, false, 'handleBlueprintUpload:error');
          }
        },
        
        handleBlueprintError: (error: string) => {
          console.error('Blueprint upload error:', error);
          set({ 
            processingError: `Blueprint processing failed: ${error}`,
            isProcessing: false 
          }, false, 'handleBlueprintError');
        },
        
        clearBlueprintData: () => {
          set({
            blueprintJobId: null,
            professionalAnalysis: null,
            isProcessing: false,
            processingError: null
          }, false, 'clearBlueprintData');
        },
        
        // Computed getters
        canNavigateBack: () => {
          const { currentStep } = get();
          return currentStep !== 'project';
        },
        
        isComplete: () => {
          const { currentStep, inputMethod, projectInfo, buildingInfo, rooms } = get();
          return currentStep === 'results' && 
            (inputMethod === 'blueprint' || Boolean(projectInfo && buildingInfo && rooms.length > 0));
        },
        
        hasCalculationResults: () => {
          const { loadCalculation, recommendations } = get();
          return loadCalculation !== null && recommendations.length > 0;
        },
        
        hasBlueprintAnalysis: () => {
          const { professionalAnalysis } = get();
          return professionalAnalysis !== null;
        },
      }),
      {
        name: 'autohvac-app-store',
        // Only persist non-sensitive data
        partialize: (state) => ({
          currentStep: state.currentStep,
          projectInfo: state.projectInfo,
          buildingInfo: state.buildingInfo,
          rooms: state.rooms,
          inputMethod: state.inputMethod,
          // Don't persist calculations or analysis data - they should be regenerated
        }),
      }
    ),
    { name: 'AutoHVAC Store' }
  )
);